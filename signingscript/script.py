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
from signingscript.task import download_files, validate_task_schema
from signingscript.utils import load_json
from signingscript.push_apk import PushAPK


log = logging.getLogger(__name__)


class PushApkContext(Context):
    def craft_push_config(self, apks):
        # Example (config={
        #    'package_name': 'org.mozilla.fennec_aurora',
        #    'track': 'alpha',
        #    'service_account': 'johan-lorenzo-service-account@boxwood-axon-825.iam.gserviceaccount.com',
        #    'credentials': 'googleplay.p12',
        #    'apk_x86': './fennec-46.0a2.en-US.android-i386.apk',
        #    'apk_armv7_v15': './fennec-46.0a2.en-US.android-arm.apk',
        # })

        push_apk_config = {
            'apk_{}'.format(apk_type): os.path.join(self.config['work_dir'], apk_path)
            for apk_type, apk_path in apks.items()
        }
        push_apk_config['service_account'] = 'johan-lorenzo-service-account@boxwood-axon-825.iam.gserviceaccount.com'
        push_apk_config['credentials'] = os.path.join('/home/jlorenzo/git/mozilla-releng/signingscript/signingscript/data/', 'googleplay.p12')

        push_apk_config['track'] = 'alpha'
        push_apk_config['package_name'] = 'org.mozilla.fennec_aurora'
        return push_apk_config


# async_main {{{1
async def async_main(context):
    context.task = scriptworker.client.get_task(context.config)
    log.info("validating task")
    validate_task_schema(context)

    with aiohttp.ClientSession() as base_ssl_session:
        orig_session = context.session
        context.session = base_ssl_session
        downloaded_apks = await download_files(context)
        context.session = orig_session

    log.info('Pushing APKs to playstore...')
    push_apk = PushAPK(config=context.craft_push_config(downloaded_apks))
    push_apk.run()
    log.info('Done!')


# config {{{1
def get_default_config():
    """ Create the default config to work from.
    """
    cwd = os.getcwd()
    parent_dir = os.path.dirname(cwd)

    default_config = {
        'work_dir': os.path.join(parent_dir, 'work_dir'),
        'schema_file': os.path.join(cwd, 'signingscript', 'data', 'signing_task_schema.json'),
        'valid_artifact_schemes': ['https'],
        'valid_artifact_netlocs': ['queue.taskcluster.net'],
        'valid_artifact_path_regexes': [r'''/v1/task/(?P<taskId>[^/]+)(/runs/\d+)?/artifacts/(?P<filepath>.*)$'''],
        'verbose': False,
    }
    return default_config


# main {{{1
def usage():
    print("Usage: {} CONFIG_FILE".format(sys.argv[0]), file=sys.stderr)
    sys.exit(1)


def main(name=None, config_path=None):
    if name not in (None, '__main__'):
        return
    context = PushApkContext()
    context.config = get_default_config()
    if config_path is None:
        if len(sys.argv) != 2:
            usage()
        config_path = sys.argv[1]
    context.config.update(load_json(path=config_path))
    if context.config.get('verbose'):
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=log_level
    )
    logging.getLogger("taskcluster").setLevel(logging.WARNING)
    loop = asyncio.get_event_loop()

    with aiohttp.ClientSession() as session:
        context.session = session
        try:
            loop.run_until_complete(async_main(context))
        except ScriptWorkerTaskException as exc:
            traceback.print_exc()
            sys.exit(exc.exit_code)
    loop.close()


main(name=__name__)
