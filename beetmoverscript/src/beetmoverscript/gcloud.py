#!/usr/bin/env python

import base64
import logging
import mimetypes
import os
import tempfile
from datetime import datetime

from google.api_core.exceptions import Forbidden
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import artifactregistry_v1
from google.cloud.storage import Bucket, Client
from google.cloud.storage.retry import DEFAULT_RETRY
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
    filename = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if filename and os.path.isfile(filename):
        os.remove(filename)


def setup_gcloud(context):
    gcs_creds = get_credentials(context, "gcloud")
    if isinstance(gcs_creds, str) and len(gcs_creds) > 0:
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


async def upload_to_gcs(context, target_path, path, expiry=None):
    product = get_product_name(context.task, context.config)
    mime_type = mimetypes.guess_type(path)[0]
    if not mime_type:
        raise ScriptWorkerTaskException("Unable to discover valid mime-type for path ({}), mimetypes.guess_type() returned {}".format(path, mime_type))
    bucket_name = get_bucket_name(context, product, "gcloud")

    bucket = Bucket(context.gcs_client, name=bucket_name)
    blob = bucket.blob(target_path)
    blob.content_type = mime_type
    blob.cache_control = "public, max-age=%d" % CACHE_CONTROL_MAXAGE
    if expiry:
        blob.custom_time = datetime.fromisoformat(expiry)

    if blob.exists():
        log.warning("upload_to_gcs: Overriding file: %s", target_path)
    log.info("upload_to_gcs: %s -> Bucket: gs://%s/%s  (custom_time: %s)", path, bucket_name, target_path, expiry)
    """
    In certain cases, such as when handling *-latest directories, we need to overwrite existing file blobs.
    Since we don't use `DELETE` requests in beetmover, the race condition mentioned in the GCS documentation [1] should not occur.
    A race condition may arise if multiple tasks run simultaneously and attempt to upload to the same file key.
    However, this issue exists independently of retries, so we proceed with retrying.
    That's why we explicitly provide `retry=DEFAULT_RETRY` instead of utilizing `if_generation_match` [2], as recommended in the documentation.

    [1] https://cloud.google.com/storage/docs/request-preconditions#multiple_request_retries
    [2] https://cloud.google.com/storage/docs/xml-api/reference-headers#xgoogifgenerationmatch
    """
    return blob.upload_from_filename(path, content_type=mime_type, retry=DEFAULT_RETRY)


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

    if context.resource_type == "apt-repo":
        import_artifacts_gcs_source = artifactregistry_v1.ImportAptArtifactsGcsSource
        import_artifacts_request = artifactregistry_v1.ImportAptArtifactsRequest
        import_artifacts = context.gar_client.import_apt_artifacts
    elif context.resource_type == "yum-repo":
        import_artifacts_gcs_source = artifactregistry_v1.ImportYumArtifactsGcsSource
        import_artifacts_request = artifactregistry_v1.ImportYumArtifactsRequest
        import_artifacts = context.gar_client.import_yum_artifacts
    else:
        raise Exception(f"Artifact Registry resource must be one of [apt-repo, yum-repo]. Got {context.resource_type} instead.")

    bucket_name = get_bucket_name(context, product, "gcloud")
    uris = [f"gs://{bucket_name}/{gcs_source}" for gcs_source in context.task["payload"]["gcs_sources"]]
    gcs_source = import_artifacts_gcs_source(
        uris=uris,
        use_wildcards=False,
    )
    log.info(gcs_source)

    request = import_artifacts_request(
        gcs_source=gcs_source,
        parent=repository.name,
    )
    log.info(request)

    async_operation = await import_artifacts(request)
    result = await async_operation.result()
    if len(result.errors) != 0:
        log.error(result.errors)
        raise Exception("Got error(s) trying to import artifacts: {}", result.errors)
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
    exclude = context.task["payload"].get("exclude", []) + list(RELEASE_EXCLUDE)

    for blob_path in candidates_blobs.keys():
        if "/partner-repacks/" in blob_path:
            partner_match = get_partner_match(blob_path, candidates_prefix, push_partners)
            if partner_match:
                blobs_to_copy[blob_path] = blob_path.replace(
                    get_partner_candidates_prefix(candidates_prefix, partner_match),
                    get_partner_releases_prefix(product, version, partner_match),
                )
            else:
                log.debug("Excluding partner repack {}".format(blob_path))
        elif not matches_exclude(blob_path, exclude):
            blobs_to_copy[blob_path] = blob_path.replace(candidates_prefix, releases_prefix)
        else:
            log.debug("Excluding {}".format(blob_path))

    move_artifacts(client, bucket_name, blobs_to_copy, candidates_blobs, releases_blobs)


def list_bucket_objects_gcs(client, bucket, prefix):
    return {blob.name: blob.md5_hash for blob in list(client.list_blobs(bucket, prefix=prefix))}


def move_artifacts(client, bucket_name, blobs_to_copy, candidates_blobs, releases_blobs):
    """Moves artifacts in a bucket from one location to another.
    It does not copy any metadata such as custom_time
    """
    bucket = Bucket(client, bucket_name)
    for source, destination in blobs_to_copy.items():
        if destination in releases_blobs:
            # compare md5
            if candidates_blobs[source] != releases_blobs[destination]:
                raise ScriptWorkerTaskException(
                    "{} already exists with different content (src etag: {}, dest etag: {}), aborting".format(
                        destination,
                        candidates_blobs[source],
                        releases_blobs[destination],
                    )
                )
            else:
                log.warning("{} already exists with the same content ({}), skipping copy".format(destination, releases_blobs[destination]))
        else:
            log.info("Copying {} to {}".format(source, destination))
            source_blob = bucket.get_blob(source)
            dest_blob = bucket.blob(destination)
            # We need to set the data payload with some information so the metadata is NOT copied over.
            # This prevents custom_time metadata from being copied unintentionally
            # https://cloud.google.com/storage/docs/json_api/v1/objects/rewrite#request-body
            dest_blob._properties["name"] = destination
            dest_blob._properties["bucket"] = bucket.name
            dest_blob.content_type = source_blob.content_type
            dest_blob.cache_control = source_blob.cache_control
            dest_blob.rewrite(source=source_blob, retry=DEFAULT_RETRY)
