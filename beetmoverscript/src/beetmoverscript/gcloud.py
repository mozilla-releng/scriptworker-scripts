#!/usr/bin/env python

import base64
import logging
import mimetypes
import os
import tempfile

from google.api_core.exceptions import Forbidden
from google.auth.exceptions import DefaultCredentialsError
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
    matches_exclude,
)

log = logging.getLogger(__name__)


def cleanup_gcloud(context):
    # Cleanup credentials file if gcs client is present
    if hasattr(context, "gcs_client") and context.gcs_client:
        os.remove(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])


def setup_gcloud(context):
    gcs_creds = get_credentials(context, "gcloud")
    if type(gcs_creds) is str and len(gcs_creds) > 0:
        setup_gcs_credentials(gcs_creds)
        set_gcs_client(context)
    else:
        log.info("No GCS credentials found, skipping")


def set_gcs_client(context):
    product = get_product_name(context.task, context.config)

    def handle_exception(e):
        if get_fail_task_on_error(context.config["clouds"], context.bucket, "gcloud"):
            raise e
        log.error(e)

    # Only used for exception handling/logging
    bucket = "<unset>"
    try:
        client = Client()
        bucket = client.bucket(get_bucket_name(context, product, "gcloud"))
        if not bucket.exists():
            log.warning(f"GCS bucket {bucket} doesn't exit. Skipping GCS uploads.")
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
    context.gcs_client = client


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
