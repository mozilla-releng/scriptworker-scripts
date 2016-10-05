#!/usr/bin/env python
"""Beetmover script
"""
from copy import deepcopy

import aiohttp
import asyncio
import boto3
import logging
import mimetypes
import os
import sys
import traceback

from scriptworker.client import get_task, validate_artifact_url
from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException, ScriptWorkerRetryException
from scriptworker.utils import retry_async, download_file, raise_future_exceptions

from beetmoverscript.constants import MIME_MAP
from beetmoverscript.task import validate_task_schema
from beetmoverscript.utils import load_json, generate_candidates_manifest

log = logging.getLogger(__name__)


# async_main {{{1
async def async_main(context):
    # 1. parse the task
    context.task = get_task(context.config)  # e.g. $cfg['work_dir']/task.json
    # 2. validate the task
    validate_task_schema(context)
    # 3. generate manifest
    manifest = generate_candidates_manifest(context)
    # 4. for each artifact in manifest
    #   a. download artifact
    #   b. upload to candidates/dated location
    await move_beets(context, manifest)
    # 5. copy to releases/latest location
    log.info('Success!')


async def move_beets(context, manifest):
    beets = []
    for locale in manifest['mapping']:
        for deliverable in manifest['mapping'][locale]:
            source = os.path.join(manifest["artifact_base_url"],
                                  manifest['mapping'][locale][deliverable]['artifact'])
            dest_dated = os.path.join(manifest["s3_prefix_dated"],
                                      manifest['mapping'][locale][deliverable]['s3_key'])
            dest_latest = os.path.join(manifest["s3_prefix_latest"],
                                       manifest['mapping'][locale][deliverable]['s3_key'])
            beets.append(
                asyncio.ensure_future(
                    move_beet(context, source, destinations=(dest_dated, dest_latest))
                )
            )
    await raise_future_exceptions(beets)


async def move_beet(context, source, destinations):
    beet_config = deepcopy(context.config)
    beet_config.setdefault('valid_artifact_task_ids', context.task['dependencies'])
    rel_path = validate_artifact_url(beet_config, source)
    abs_file_path = os.path.join(context.config['work_dir'], rel_path)

    await retry_download(context=context, url=source, path=abs_file_path)
    await retry_upload(context=context, destinations=destinations, path=abs_file_path)


async def retry_upload(context, destinations, path):
    # TODO rather than upload twice, use something like boto's bucket.copy_key
    #   probably via the awscli subproc directly.
    # For now, this will be faster than using copy_key() as boto would block
    uploads = []
    for dest in destinations:
        uploads.append(
            asyncio.ensure_future(
                upload_to_s3(context=context, s3_key=dest, path=path)
            )
        )
    await raise_future_exceptions(uploads)


async def retry_download(context, url, path):
    return await retry_async(download_file, args=(context, url, path),
                             kwargs={'session': context.session})


async def put(context, url, headers, abs_filename, session=None):
    with open(abs_filename, "rb") as fh:
        async with session.put(url, data=fh, headers=headers, compress=False) as resp:
            log.info(resp.status)
            response_text = await resp.text()
            log.info(response_text)
            if resp.status not in (200, 204):
                raise ScriptWorkerRetryException(
                    "Bad status {}".format(resp.status),
                )
    return resp


async def upload_to_s3(context, s3_key, path):
    api_kwargs = {
        'Bucket': context.config['s3']['bucket'],
        'Key': s3_key,
        'ContentType': mimetypes.guess_type(path)[0]
    }
    headers = {
        'Content-Type': mimetypes.guess_type(path)[0]
    }
    creds = context.config['s3']['credentials']
    s3 = boto3.client('s3', aws_access_key_id=creds['id'], aws_secret_access_key=creds['key'],)
    url = s3.generate_presigned_url('put_object', api_kwargs, ExpiresIn=30, HttpMethod='PUT')

    await retry_async(put, args=(context, url, headers, path),
                      kwargs={'session': context.session})


# main {{{1
def usage():
    print("Usage: {} CONFIG_FILE".format(sys.argv[0]), file=sys.stderr)
    sys.exit(1)


def setup_config(config_path):
    if config_path is None:
        if len(sys.argv) != 2:
            usage()
        config_path = sys.argv[1]
    context = Context()
    context.config = {}
    context.config.update(load_json(path=config_path))
    return context


def setup_logging():
    log_level = logging.DEBUG
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=log_level
    )
    logging.getLogger("taskcluster").setLevel(logging.WARNING)


def setup_mimetypes():
    mimetypes.init()
    # in py3 we must exhaust the map so that add_type is actually invoked
    list(map(
        lambda ext_mimetype: mimetypes.add_type(ext_mimetype[1], ext_mimetype[0]), MIME_MAP.items()
    ))


def main(name=None, config_path=None):
    if name not in (None, '__main__'):
        return

    context = setup_config(config_path)
    setup_logging()
    setup_mimetypes()

    loop = asyncio.get_event_loop()
    conn = aiohttp.TCPConnector()
    with aiohttp.ClientSession(connector=conn) as session:
        context.session = session
        try:
            loop.run_until_complete(async_main(context))
        except ScriptWorkerTaskException as exc:
            traceback.print_exc()
            sys.exit(exc.exit_code)
    loop.close()

main(name=__name__)
