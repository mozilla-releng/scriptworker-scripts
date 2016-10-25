#!/usr/bin/env python3
""" PushAPK main script
"""
import aiohttp
import asyncio
import logging
import os
import sys
import traceback

import scriptworker.client
from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException

from pushapkscript import jarsigner
from pushapkscript.task import download_files, validate_task_schema, extract_channel
from pushapkscript.utils import load_json
from pushapkscript.googleplay import publish_to_googleplay


log = logging.getLogger(__name__)


# async_main {{{1
async def async_main(context):
    context.task = scriptworker.client.get_task(context.config)
    log.info("validating task")
    validate_task_schema(context)

    log.info('Downloading APKs...')
    downloaded_apks = await download_files(context)

    log.info('Verifying APKs\' signatures...')
    channel = extract_channel(context.task)
    for _, apk_path in downloaded_apks.items():
        jarsigner.verify(context, apk_path, channel)

    log.info('Pushing APKs to Google Play Store...')
    publish_to_googleplay(context, downloaded_apks)

    log.info('Done!')


def get_default_config():
    """ Create the default config to work from.
    """
    cwd = os.getcwd()
    parent_dir = os.path.dirname(cwd)

    default_config = {
        'work_dir': os.path.join(parent_dir, 'work_dir'),
        'schema_file': os.path.join(cwd, 'pushapkscript', 'data', 'pushapk_task_schema.json'),
        'valid_artifact_schemes': ['https'],
        'valid_artifact_netlocs': ['queue.taskcluster.net'],
        'valid_artifact_path_regexes': [r'''/v1/task/(?P<taskId>[^/]+)(/runs/\d+)?/artifacts/(?P<filepath>.*)$'''],
        'verbose': False,
    }
    return default_config


def usage():
    print("Usage: {} CONFIG_FILE".format(sys.argv[0]), file=sys.stderr)
    sys.exit(1)


def main(name=None, config_path=None):
    if name not in (None, '__main__'):
        return
    context = Context()
    context.config = get_default_config()
    if config_path is None:
        if len(sys.argv) != 2:
            usage()
        config_path = sys.argv[1]
    context.config.update(load_json(path=config_path))

    logging.basicConfig(**craft_logging_config(context))
    logging.getLogger('taskcluster').setLevel(logging.WARNING)

    loop = asyncio.get_event_loop()
    with aiohttp.ClientSession() as session:
        context.session = session
        try:
            loop.run_until_complete(async_main(context))
        except ScriptWorkerTaskException as exc:
            traceback.print_exc()
            sys.exit(exc.exit_code)
    loop.close()


def craft_logging_config(context):
    return {
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'level': logging.DEBUG if context.config.get('verbose') else logging.INFO
    }


main(name=__name__)
