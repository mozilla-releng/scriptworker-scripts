#!/usr/bin/env python
"""Beetmover script
"""
import asyncio
import logging
import os
import sys
import traceback
import mimetypes
import aiohttp
import boto3

from scriptworker.client import get_task
from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException, ScriptWorkerRetryException
from scriptworker.utils import retry_async, raise_future_exceptions

from beetmoverscript.constants import MIME_MAP
from beetmoverscript.task import (validate_task_schema, add_balrog_manifest_to_artifacts,
                                  get_upstream_artifacts, get_initial_release_props_file,
                                  validate_task_scopes, add_checksums_to_artifacts)
from beetmoverscript.utils import (load_json, get_hash, get_release_props,
                                   generate_beetmover_manifest, get_size)

log = logging.getLogger(__name__)


# async_main {{{1
async def async_main(context):
    # balrog_manifest is written and uploaded as an artifact which is used by a subsequent
    # balrogworker task in the release graph. Balrogworker uses this manifest to submit
    # release blob info with things like mar filename, size, etc
    context.balrog_manifest = list()

    # the checksums manifest is written and uploaded as an artifact which is used
    # by a subsequent signing task and again by another beetmover task to
    # upload it along with the other artifacts
    context.checksums = dict()

    # determine and validate the task schema along with its scopes
    context.task = get_task(context.config)  # e.g. $cfg['work_dir']/task.json
    validate_task_schema(context)

    # determine artifacts to beetmove
    context.artifacts_to_beetmove = get_upstream_artifacts(context)
    # determine the release properties
    context.release_props = get_release_props(get_initial_release_props_file(context))

    # generate beetmover mapping manifest
    mapping_manifest = generate_beetmover_manifest(context.config,
                                                   context.task,
                                                   context.release_props)
    # validate scopes to prevent beetmoving in the wrong place
    validate_task_scopes(context, mapping_manifest)

    # for each artifact in manifest
    #   a. map each upstream artifact to pretty name release bucket format
    #   b. upload to candidates/dated location
    await move_beets(context, context.artifacts_to_beetmove, mapping_manifest)

    #  write balrog_manifest to a file and add it to list of artifacts
    if context.task["payload"]["update_manifest"]:
        add_balrog_manifest_to_artifacts(context)
    # determine the correct checksum filename and generate it, adding it to
    # the list of artifacts afterwards
    add_checksums_to_artifacts(context)

    log.info('Success!')


async def move_beets(context, artifacts_to_beetmove, manifest):
    beets = []
    for locale in artifacts_to_beetmove:
        for artifact in artifacts_to_beetmove[locale]:
            source = artifacts_to_beetmove[locale][artifact]
            pretty_name = manifest['mapping'][locale][artifact]['s3_key']
            dest_dated = os.path.join(manifest["s3_prefix_dated"],
                                      pretty_name)
            dest_latest = os.path.join(manifest["s3_prefix_latest"],
                                       pretty_name)
            balrog_manifest = manifest['mapping'][locale][artifact].get('update_balrog_manifest')
            beets.append(
                asyncio.ensure_future(
                    move_beet(context, source, destinations=(dest_dated, dest_latest),
                              locale=locale, update_balrog_manifest=balrog_manifest,
                              pretty_name=pretty_name)
                )
            )
    await raise_future_exceptions(beets)


async def move_beet(context, source, destinations, locale,
                    update_balrog_manifest, pretty_name):
    await retry_upload(context=context, destinations=destinations, path=source)

    if context.checksums.get(pretty_name) is None:
        context.checksums[pretty_name] = {
            algo: get_hash(source, algo) for algo in context.config['checksums_digests']
        }
        context.checksums[pretty_name]['size'] = get_size(source)

    if update_balrog_manifest:
        context.balrog_manifest.append(
            enrich_balrog_manifest(context, pretty_name, locale, destinations)
        )


def enrich_balrog_manifest(context, pretty_name, locale, destinations):
    release_props = context.release_props
    checksums = context.checksums

    if release_props["branch"] == 'date':
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
        url_replacements = [['http://archive.mozilla.org/pub', 'http://download.cdn.mozilla.net/pub']]

    return {
        "tc_nightly": True,
        "completeInfo": [{
            "hash": checksums[pretty_name][release_props["hashType"]],
            "size": checksums[pretty_name]['size'],
            "url": url
        }],

        "appName": release_props["appName"],
        "appVersion": release_props["appVersion"],
        "branch": release_props["branch"],
        "buildid": release_props["buildid"],
        "extVersion": release_props["appVersion"],
        "hashType": release_props["hashType"],
        "locale": locale if not locale == 'multi' else 'en-US',
        "platform": release_props["stage_platform"],
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


async def put(context, url, headers, abs_filename, session=None):
    session = session or context.session
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
    app = context.release_props['appName'].lower()
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
    conn = aiohttp.TCPConnector(limit=context.config['aiohttp_max_connections'])
    with aiohttp.ClientSession(connector=conn) as session:
        context.session = session
        try:
            loop.run_until_complete(async_main(context))
        except ScriptWorkerTaskException as exc:
            traceback.print_exc()
            sys.exit(exc.exit_code)
    loop.close()


main(name=__name__)
