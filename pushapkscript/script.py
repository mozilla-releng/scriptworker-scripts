#!/usr/bin/env python3
""" PushAPK main script
"""
import contextlib
import logging
import os

from scriptworker import client, artifacts
from scriptworker.exceptions import TaskVerificationError
from pushapkscript import googleplay, jarsigner, task, manifest
from pushapkscript.exceptions import ConfigValidationError


log = logging.getLogger(__name__)


async def async_main(context):
    android_product = task.extract_android_product_from_scopes(context)
    product_config = _get_product_config(context, android_product)
    contact_google_play = not bool(context.config.get('do_not_contact_google_play'))

    logging.getLogger('oauth2client').setLevel(logging.WARNING)
    _log_warning_forewords(contact_google_play, context.task['payload'])

    log.info('Verifying upstream artifacts...')
    artifacts_per_task_id, failed_artifacts_per_task_id = artifacts.get_upstream_artifacts_full_paths_per_task_id(context)

    all_apks_paths = [
        artifact
        for artifacts_list in artifacts_per_task_id.values()
        for artifact in artifacts_list
        if artifact.endswith('.apk')
    ]

    log.info('Verifying APKs\' signatures...')
    for apk_path in all_apks_paths:
        jarsigner.verify(context, apk_path)
        manifest.verify(product_config, apk_path)

    if product_config['update_google_play_strings']:
        log.info('Finding whether Google Play strings can be updated...')
        strings_path = googleplay.get_google_play_strings_path(
            artifacts_per_task_id, failed_artifacts_per_task_id
        )
    else:
        log.warning('This product does not upload strings automatically. Skipping Google Play strings search.')
        strings_path = None

    log.info('Delegating publication to mozapkpublisher...')
    with contextlib.ExitStack() as stack:
        files = [stack.enter_context(open(apk_file_name)) for apk_file_name in all_apks_paths]
        strings_file = stack.enter_context(open(strings_path)) if strings_path is not None else None
        googleplay.publish_to_googleplay(context.task['payload'], product_config, files, contact_google_play,
                                         strings_file)

    log.info('Done!')


def _get_product_config(context, android_product):
    try:
        products = context.config['products']
    except KeyError:
        raise ConfigValidationError('"products" is not part of the configuration')

    try:
        return products[android_product]
    except KeyError:
        raise TaskVerificationError('Android "{}" does not exist in the configuration of this instance.\
    Are you sure you allowed to push such APK?'.format(android_product))


def _log_warning_forewords(contact_google_play, task_payload):
    if contact_google_play:
        if googleplay.should_commit_transaction(task_payload):
            log.warning('You will publish APKs to Google Play. This action is irreversible,\
if no error is detected either by this script or by Google Play.')
        else:
            log.warning('APKs will be submitted to Google Play, but no change will not be committed.')
    else:
        log.warning('This pushapk instance is not allowed to talk to Google Play. *All* requests will be mocked.')


def get_default_config():
    cwd = os.getcwd()
    parent_dir = os.path.dirname(cwd)

    return {
        'work_dir': os.path.join(parent_dir, 'work_dir'),
        'schema_file': os.path.join(os.path.dirname(__file__), 'data', 'pushapk_task_schema.json'),
        'verbose': False,
    }


def main(config_path=None):
    client.sync_main(async_main, config_path=config_path, default_config=get_default_config())


__name__ == '__main__' and main()
