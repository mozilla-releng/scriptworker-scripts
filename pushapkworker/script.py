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

from pushapkworker.task import download_files, validate_task_schema
from pushapkworker.utils import load_json
from pushapkworker.jarsigner import JarSigner


log = logging.getLogger(__name__)


class PushApkContext(Context):
    def craft_push_config(self, apks):
        push_apk_config = {'apk_{}'.format(apk_type): apk_path for apk_type, apk_path in apks.items()}
        push_apk_config['service_account'] = self.config['google_play_service_account']
        push_apk_config['credentials'] = self.config['google_play_certificate']

        push_apk_config['track'] = self.task['payload']['google_play_track']
        push_apk_config['package_name'] = self.config['google_play_package_name']
        return push_apk_config


# async_main {{{1
async def async_main(context, jar_signer):
    context.task = scriptworker.client.get_task(context.config)
    log.info("validating task")
    validate_task_schema(context)

    log.info('Downloading APKs...')
    with aiohttp.ClientSession() as base_ssl_session:
        orig_session = context.session
        context.session = base_ssl_session
        downloaded_apks = await download_files(context)
        context.session = orig_session

    log.info('Verifying APKs\' signatures...')
    for _, apk_path in downloaded_apks.items():
        jar_signer.verify(apk_path)

    log.info('Pushing APKs to Google Play Store...')

    # XXX Import done here in order to mock the dependency out
    from mozapkpublisher.push_apk import PushAPK
    push_apk = PushAPK(config=context.craft_push_config(downloaded_apks))
    push_apk.run()
    log.info('Done!')


def get_default_config():
    """ Create the default config to work from.
    """
    cwd = os.getcwd()
    parent_dir = os.path.dirname(cwd)

    default_config = {
        'work_dir': os.path.join(parent_dir, 'work_dir'),
        'schema_file': os.path.join(cwd, 'pushapkworker', 'data', 'signing_task_schema.json'),
        'valid_artifact_schemes': ['https'],
        'valid_artifact_netlocs': ['queue.taskcluster.net'],
        'valid_artifact_path_regexes': [r'''/v1/task/(?P<taskId>[^/]+)(/runs/\d+)?/artifacts/(?P<filepath>.*)$'''],
        'verbose': False,
    }
    return default_config


def usage():
    print("Usage: {} CONFIG_FILE".format(sys.argv[0]), file=sys.stderr)
    sys.exit(1)


def setup_logging(context):
    if context.config.get('verbose'):
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=log_level
    )
    logging.getLogger('taskcluster').setLevel(logging.WARNING)


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
    setup_logging(context)

    jar_signer = JarSigner(context)

    loop = asyncio.get_event_loop()
    with aiohttp.ClientSession() as session:
        context.session = session
        try:
            loop.run_until_complete(async_main(context, jar_signer))
        except ScriptWorkerTaskException as exc:
            traceback.print_exc()
            sys.exit(exc.exit_code)
    loop.close()


main(name=__name__)
