#!/usr/bin/env python

import base64
import logging
import mimetypes
import os
import tempfile

from google.api_core.exceptions import Forbidden
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import artifactregistry_v1
from google.cloud.storage import Bucket, Client
from scriptworker.exceptions import ScriptWorkerTaskException

from beetmoverscript.constants import CACHE_CONTROL_MAXAGE, RELEASE_EXCLUDE
from beetmoverscript.utils import (
    get_bucket_name,
    get_candidates_prefix,
    get_credentials,
    get_fail_task_on_error,
    get_partner_candidates_prefix,
    get_partner_match,
    get_partner_releases_prefix,
    get_product_name,
    get_releases_prefix,
    get_resource_location,
    get_resource_name,
    get_resource_project,
    matches_exclude,
)

log = logging.getLogger(__name__)


def cleanup_gcloud(context):
    filename = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    if os.path.isfile(filename):
        os.remove(filename)


def setup_gcloud(context):
    gcs_creds = get_credentials(context, "gcloud")
    if type(gcs_creds) is str and len(gcs_creds) > 0:
        setup_gcs_credentials(gcs_creds)
        set_gcp_client(context)
    else:
        log.info("No GCS credentials found, skipping")


def _get_gcs_client(context, product):
    """Set up a google-cloud-storage client"""

    def handle_exception(e):
        if get_fail_task_on_error(context.config["clouds"], context.resource, "gcloud"):
            raise e
        log.error(e)

    # Only used for exception handling/logging
    bucket = "<unset>"
    try:
        client = Client()
        bucket = client.bucket(get_bucket_name(context, product, "gcloud"))
        if not bucket.exists():
            log.warning(f"GCS bucket {bucket} doesn't exist. Skipping GCS uploads.")
            return
    except Forbidden as e:
        log.warning(f"GCS credentials don't have access to {bucket}. Skipping GCS uploads.")
        handle_exception(e)
        return
    except DefaultCredentialsError as e:
        log.warning("GCS credential error. Skipping GCS uploads.")
        handle_exception(e)
        return
    except Exception as e:
        log.warning("Unknown error setting GCS credentials.")
        handle_exception(e)
        return
    log.info(f"Found GCS bucket {bucket} - proceeding with GCS uploads.")
    return client


def _get_artifact_registry_client(context, product):
    """Set up a google-cloud-artifact-registry client"""
    client = artifactregistry_v1.ArtifactRegistryAsyncClient()
    return client


def set_gcp_client(context):
    product = get_product_name(context.task, context.config)
    if context.resource_type in ("yum-repo", "apt-repo"):
        context.gar_client = _get_artifact_registry_client(context, product)
    else:
        context.gcs_client = _get_gcs_client(context, product)


def setup_gcs_credentials(raw_creds):
    fp = tempfile.NamedTemporaryFile(delete=False)
    fp.write(base64.decodebytes(raw_creds.encode("ascii")))
    fp.close()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = fp.name


async def upload_to_gcs(context, target_path, path):
    product = get_product_name(context.task, context.config)
    mime_type = mimetypes.guess_type(path)[0]
    if not mime_type:
        raise ScriptWorkerTaskException("Unable to discover valid mime-type for path ({}), " "mimetypes.guess_type() returned {}".format(path, mime_type))
    bucket_name = get_bucket_name(context, product, "gcloud")

    bucket = Bucket(context.gcs_client, name=bucket_name)
    blob = bucket.blob(target_path)
    blob.content_type = mime_type
    blob.cache_control = "public, max-age=%d" % CACHE_CONTROL_MAXAGE

    if blob.exists():
        log.warn("upload_to_gcs: Overriding file: %s", target_path)
    log.info("upload_to_gcs: %s -> Bucket: gs://%s/%s", path, bucket_name, target_path)

    return blob.upload_from_filename(path, content_type=mime_type)


def build_artifact_registry_gcs_source(context, product):
    bucket_name = get_bucket_name(context, product, "gcloud")
    gcs_source_kwargs = {
        "uris": [f"gs://{bucket_name}/{gcs_source}" for gcs_source in context.task["payload"]["gcs_sources"]],
        "use_wildcards": False,
    }
    if context.resource_type == "apt-repo":
        return artifactregistry_v1.ImportAptArtifactsGcsSource(**gcs_source_kwargs)
    if context.resource_type == "yum-repo":
        return artifactregistry_v1.ImportYumArtifactsGcsSource(**gcs_source_kwargs)
    raise Exception("Artifact Registry resource must be one of [apt-repo, yum-repo]")


def build_artifact_registry_import_artifacts_request(context, repository, gcs_source):
    import_request_kwargs = {
        "gcs_source": gcs_source,
        "parent": repository.name,
    }
    if context.resource_type == "apt-repo":
        return artifactregistry_v1.ImportAptArtifactsRequest(**import_request_kwargs)
    if context.resource_type == "yum-repo":
        return artifactregistry_v1.ImportYumArtifactsRequest(**import_request_kwargs)
    raise Exception("Artifact Registry resource must be one of [apt-repo, yum-repo]")


def do_artifact_registry_import_artifacts_request(context, import_artifacts_request):
    if context.resource_type == "apt-repo":
        return context.gar_client.import_apt_artifacts(request=import_artifacts_request)
    if context.resource_type == "yum-repo":
        return context.gar_client.import_yum_artifacts(request=import_artifacts_request)
    raise Exception("Artifact Registry resource must be one of [apt-repo, yum-repo]")


async def import_from_gcs_to_artifact_registry(context):
    """Imports release artifacts from gcp cloud storage to gcp artifact registry"""
    product = get_product_name(context.task, context.config)
    project = get_resource_project(context, product, "gcloud")
    location = get_resource_location(context, product, "gcloud")
    repository_name = get_resource_name(context, product, "gcloud")
    parent = f"projects/{project}/locations/{location}/repositories/{repository_name}"
    get_repo_request = artifactregistry_v1.GetRepositoryRequest(
        name=parent,
    )

    repository = await context.gar_client.get_repository(request=get_repo_request)
    log.info(repository)

    gcs_source = build_artifact_registry_gcs_source(context, product)
    log.info(gcs_source)

    import_artifacts_request = build_artifact_registry_import_artifacts_request(context, repository, gcs_source)
    log.info(import_artifacts_request)

    async_operation = await do_artifact_registry_import_artifacts_request(context, import_artifacts_request)
    result = await async_operation.result()
    if len(result.errors) != 0:
        log.error(result.errors)
    else:
        log.info(result)


async def push_to_releases_gcs(context):
    product = context.task["payload"]["product"]
    build_number = context.task["payload"]["build_number"]
    version = context.task["payload"]["version"]
    bucket_name = get_bucket_name(context, product, "gcloud")
    client = context.gcs_client

    candidates_prefix = get_candidates_prefix(product, version, build_number)
    releases_prefix = get_releases_prefix(product, version)

    candidates_blobs = list_bucket_objects_gcs(client, bucket_name, candidates_prefix)
    releases_blobs = list_bucket_objects_gcs(client, bucket_name, releases_prefix)

    if not candidates_blobs:
        raise ScriptWorkerTaskException("No artifacts to copy from {} so there is no reason to continue.".format(candidates_prefix))

    if releases_blobs:
        log.warning("Destination {} already exists with {} keys".format(releases_prefix, len(releases_blobs)))

    blobs_to_copy = {}

    # Weed out RELEASE_EXCLUDE matches, but allow partners specified in the payload
    push_partners = context.task["payload"].get("partners", [])
    for blob_path in candidates_blobs.keys():
        if "/partner-repacks/" in blob_path:
            partner_match = get_partner_match(blob_path, candidates_prefix, push_partners)
            if partner_match:
                blobs_to_copy[blob_path] = blob_path.replace(
                    get_partner_candidates_prefix(candidates_prefix, partner_match), get_partner_releases_prefix(product, version, partner_match)
                )
            else:
                log.debug("Excluding partner repack {}".format(blob_path))
        elif not matches_exclude(blob_path, RELEASE_EXCLUDE):
            blobs_to_copy[blob_path] = blob_path.replace(candidates_prefix, releases_prefix)
        else:
            log.debug("Excluding {}".format(blob_path))

    move_artifacts(client, bucket_name, blobs_to_copy, candidates_blobs, releases_blobs)


def list_bucket_objects_gcs(client, bucket, prefix):
    return {blob.name: blob.md5_hash for blob in list(client.list_blobs(bucket, prefix=prefix))}


def move_artifacts(client, bucket_name, blobs_to_copy, candidates_blobs, releases_blobs):
    bucket = Bucket(client, bucket_name)
    for source, destination in blobs_to_copy.items():
        if destination in releases_blobs:
            # compare md5
            if candidates_blobs[source] != releases_blobs[destination]:
                raise ScriptWorkerTaskException(
                    "{} already exists with different content "
                    "(src etag: {}, dest etag: {}), aborting".format(destination, candidates_blobs[source], releases_blobs[destination])
                )
            else:
                log.warning("{} already exists with the same content ({}), " "skipping copy".format(destination, releases_blobs[destination]))
        else:
            log.info("Copying {} to {}".format(source, destination))
            source_blob = bucket.blob(source)
            bucket.copy_blob(source_blob, bucket, destination)
