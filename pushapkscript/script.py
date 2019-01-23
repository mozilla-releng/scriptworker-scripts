#!/usr/bin/env python3
""" PushAPK main script
"""
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

    logging.getLogger('oauth2client').setLevel(logging.WARNING)
    _log_warning_forewords(android_product, context.task['payload'])

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
        google_play_strings_path = googleplay.get_google_play_strings_path(
            artifacts_per_task_id, failed_artifacts_per_task_id
        )
    else:
        log.warning('This product does not upload strings automatically. Skipping Google Play strings search.')
        google_play_strings_path = None

    log.info('Delegating publication to mozapkpublisher...')
    googleplay.publish_to_googleplay(
        context.task['payload'], android_product, product_config, all_apks_paths, google_play_strings_path,
    )

    log.info('Done!')


def _get_product_config(context, android_product):
    try:
        accounts = context.config['products']
    except KeyError:
        raise ConfigValidationError('"products" is not part of the configuration')

    try:
        return accounts[android_product]
    except KeyError:
        raise TaskVerificationError('Android "{}" does not exist in the configuration of this instance.\
    Are you sure you allowed to push such APK?'.format(android_product))


def _log_warning_forewords(android_product, task_payload):
    if googleplay.is_allowed_to_push_to_google_play(android_product):
        if googleplay.should_commit_transaction(task_payload):
            log.warning('You will publish APKs to Google Play. This action is irreversible,\
if no error is detected either by this script or by Google Play.')
        else:
            log.warning('APKs will be submitted to Google Play, but no change will not be committed.')
    else:
        log.warning('You do not have the rights to reach Google Play. *All* requests will be mocked.')


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
