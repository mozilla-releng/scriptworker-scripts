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

from beetmoverscript.constants import CACHE_CONTROL_MAXAGE
from beetmoverscript.task import get_release_props
from beetmoverscript.utils import get_bucket_name, get_credentials, get_fail_task_on_error, get_product_name

log = logging.getLogger(__name__)


def cleanup_gcloud(context):
    # Cleanup credentials file if gcs client is present
    if hasattr(context, "gcs_client") and context.gcs_client:
        os.remove(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])


def setup_gcloud(context):
    gcs_creds = get_credentials(context, "gcloud")
    if type(gcs_creds) is str and len(gcs_creds) > 0:
        setup_gcs_credentials(gcs_creds)
        # TODO: maybe we should load release_props in async_main instead of each action?
        #   Needed for bucket lookup
        context.release_props = get_release_props(context)
        set_gcs_client(context)
    else:
        log.info("No GCS credentials found, skipping")


def set_gcs_client(context):
    product = get_product_name(context.release_props["appName"].lower(), context.release_props["stage_platform"])

    def handle_exception(e):
        if get_fail_task_on_error(context, "gcloud"):
            raise e
        print(e.__traceback__)

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
    product = get_product_name(context.release_props["appName"].lower(), context.release_props["stage_platform"])
    mime_type = mimetypes.guess_type(path)[0]
    if not mime_type:
        raise ScriptWorkerTaskException("Unable to discover valid mime-type for path ({}), " "mimetypes.guess_type() returned {}".format(path, mime_type))
    bucket = get_bucket_name(context, product, "gcloud")

    bucket = Bucket(context.gcs_client, name=bucket)
    blob = bucket.blob(target_path)
    blob.content_type = mime_type
    blob.cache_control = "public, max-age=%d" % CACHE_CONTROL_MAXAGE

    return blob.upload_from_filename(path, content_type=mime_type)
