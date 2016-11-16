#!/usr/bin/env python
"""Beetmover script
"""
from copy import deepcopy

import asyncio
import logging
import os
import sys
import traceback
import mimetypes
import aiohttp
import boto3

from scriptworker.client import get_task, validate_artifact_url
from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException, ScriptWorkerRetryException
from scriptworker.utils import (retry_async, download_file,
                                raise_future_exceptions, retry_request)

from beetmoverscript.constants import MIME_MAP, MANIFEST_URL_TMPL, PLATFORM_MAP
from beetmoverscript.task import validate_task_schema, add_balrog_manifest_to_artifacts
from beetmoverscript.utils import (load_json, generate_candidates_manifest,
                                   update_props, get_hash)

log = logging.getLogger(__name__)


# async_main {{{1
async def async_main(context):
    # balrog_manifest is used by a subsequent balrogworker task that points to a beetmoved artifact
    context.balrog_manifest = list()

    # 1. parse the task
    context.task = get_task(context.config)  # e.g. $cfg['work_dir']/task.json
    # 2. validate the task
    validate_task_schema(context)
    # 3 prepare manifest props file
    #   a. grab manifest props with all the useful data
    #   b. amend platform field to proper one
    context.properties = await get_props(context)
    context.properties = update_props(context.properties, PLATFORM_MAP)
    # 4. generate manifest
    manifest = generate_candidates_manifest(context)
    # 5. for each artifact in manifest
    #   a. download artifact
    #   b. upload to candidates/dated location
    await move_beets(context, manifest)
    # 6. write balrog_manifest to a file and add it to list of artifacts
    if context.task["payload"]["update_manifest"]:
        add_balrog_manifest_to_artifacts(context)
    log.info('Success!')


async def get_props(context):
    taskid_of_manifest = context.task['payload']['taskid_of_manifest']
    source = MANIFEST_URL_TMPL % taskid_of_manifest

    # extra validation check is useful for the url scheme, netloc and path
    # restrictions
    beet_config = deepcopy(context.config)
    beet_config.setdefault('valid_artifact_task_ids', context.task['dependencies'])
    validate_artifact_url(beet_config, source)

    return (await retry_request(context, source, method='get',
                                return_type='json'))['properties']


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
            balrog_manifest = manifest['mapping'][locale][deliverable].get('update_balrog_manifest')
            beets.append(
                asyncio.ensure_future(
                    move_beet(context, source, destinations=(dest_dated, dest_latest),
                              locale=locale, update_balrog_manifest=balrog_manifest)
                )
            )
    await raise_future_exceptions(beets)


async def move_beet(context, source, destinations, locale, update_balrog_manifest):
    beet_config = deepcopy(context.config)
    beet_config.setdefault('valid_artifact_task_ids', context.task['dependencies'])
    rel_path = validate_artifact_url(beet_config, source)
    abs_file_path = os.path.join(context.config['work_dir'], rel_path)

    await retry_download(context=context, url=source, path=abs_file_path)
    await retry_upload(context=context, destinations=destinations, path=abs_file_path)

    if update_balrog_manifest:
        context.balrog_manifest.append(
            enrich_balrog_manifest(context, abs_file_path, locale, destinations)
        )


def enrich_balrog_manifest(context, path, locale, destinations):
    props = context.properties

    if props["branch"] == 'date':
        # nightlies from dev branches don't usually upload to archive.m.o but
        # in this particular case we're gradually rolling out in the
        # archive.m.o under the latest-date corresponding bucket subfolder
        url = "{prefix}/{s3_key}".format(prefix="https://archive.mozilla.org",
                                         s3_key=destinations[0])
        url_replacements = []
    else:
        # we extract the dated destination as the 'latest' is useless
        url = "{prefix}/{s3_key}".format(prefix="https://archive.mozilla.org",
                                         s3_key=destinations[0])
        url_replacements = [['http://archive.mozilla.org/pub, http://download.cdn.mozilla.net/pub']]

    return {
        "tc_nightly": True,

        "completeInfo": [{
            "hash": get_hash(path, hash_type=props["hashType"]),
            "size": os.path.getsize(path),
            "url": url
        }],

        "appName": props["appName"],
        "appVersion": props["appVersion"],
        "branch": props["branch"],
        "buildid": props["buildid"],
        "extVersion": props["appVersion"],
        "hashType": props["hashType"],
        "locale": locale if not locale == 'multi' else 'en-US',
        "platform": props["stage_platform"],
        "url_replacements": url_replacements
    }


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
    app = context.properties['appName'].lower()
    api_kwargs = {
        'Bucket': context.config['s3'][app]['bucket'],
        'Key': s3_key,
        'ContentType': mimetypes.guess_type(path)[0]
    }
    headers = {
        'Content-Type': mimetypes.guess_type(path)[0]
    }
    creds = context.config['s3'][app]['credentials']
    s3 = boto3.client('s3', aws_access_key_id=creds['id'], aws_secret_access_key=creds['key'],)
    url = s3.generate_presigned_url('put_object', api_kwargs, ExpiresIn=1800, HttpMethod='PUT')

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
