#!/usr/bin/env python
"""Beetmover script
"""
from copy import deepcopy

import aiohttp
import asyncio
import logging
import os
import sys
import traceback

from scriptworker.client import get_task, validate_artifact_url
from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException
from scriptworker.utils import retry_async, download_file

from beetmoverscript.task import validate_task_schema
from beetmoverscript.utils import load_json, generate_candidates_manifest

log = logging.getLogger(__name__)


# async_main {{{1
async def async_main(context):
    log.info("Hello Scriptworker!")
    # 1. parse the task
    context.task = get_task(context.config)  # e.g. $cfg['work_dir']/task.json
    # 2. validate the task
    validate_task_schema(context)
    # 3. generate manifest
    manifest = generate_candidates_manifest(context)
    # 4. for each artifact in manifest
    #   a. download artifact
    #   b. upload to candidates/dated location
    await beetmove_bits(manifest, context)
    # 5. copy to releases/latest location
    log.info('Success!')


async def beetmove_bits(manifest, context):
    for locale in manifest['mapping']:
        for deliverable in manifest['mapping'][locale]:
            source = os.path.join(manifest["artifact_base_url"],
                                  manifest['mapping'][locale][deliverable]['artifact'])
            dest = os.path.join(manifest["s3_prefix_dated"],
                                manifest['mapping'][locale][deliverable]['s3_key'])
            await beetmove_bit(source, dest, context)


async def beetmove_bit(source, dest, context):
    await download(url=source, context=context)
    await upload(s3_key=dest, context=context)


async def download(url, context):
    download_config = deepcopy(context.config)
    download_config.setdefault('valid_artifact_task_ids', context.task['dependencies'])
    rel_path = validate_artifact_url(download_config, url)
    abs_file_path = os.path.join(context.config['work_dir'], rel_path)

    await retry_async(download_file, args=(context, url, abs_file_path),
                      kwargs={'session': context.session})


async def upload(s3_key, context):
    # hm, how to boto with async? maybe https://github.com/aio-libs/aiobotocore ?
    pass


# main {{{1
def usage():
    print("Usage: {} CONFIG_FILE".format(sys.argv[0]), file=sys.stderr)
    sys.exit(1)


def main(name=None, config_path=None):
    if name not in (None, '__main__'):
        return
    if config_path is None:
        if len(sys.argv) != 2:
            usage()
        config_path = sys.argv[1]
    context = Context()
    context.config = {}
    context.config.update(load_json(path=config_path))

    log_level = logging.DEBUG
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=log_level
    )
    logging.getLogger("taskcluster").setLevel(logging.WARNING)
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
