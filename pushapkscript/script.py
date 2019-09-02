#!/usr/bin/env python3
""" PushAPK main script
"""
import contextlib
import logging
import os

from scriptworker import client, artifacts
from scriptworker.exceptions import TaskVerificationError
from pushapkscript import publish, jarsigner, task, manifest
from pushapkscript.exceptions import ConfigValidationError
from pushapkscript.publish_config import get_publish_config

log = logging.getLogger(__name__)


async def async_main(context):
    android_product = task.extract_android_product_from_scopes(context)
    product_config = _get_product_config(context, android_product)
    publish_config = get_publish_config(product_config, context.task['payload'], android_product)
    contact_server = not bool(context.config.get('do_not_contact_server'))

    logging.getLogger('oauth2client').setLevel(logging.WARNING)
    _log_warning_forewords(contact_server, context.task['payload'])

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
        jarsigner.verify(context, publish_config, apk_path)
        manifest.verify(product_config, apk_path)

    log.info('Delegating publication to mozapkpublisher...')
    with contextlib.ExitStack() as stack:
        files = [stack.enter_context(open(apk_file_name)) for apk_file_name in all_apks_paths]
        publish.publish(context.task['payload'], product_config, publish_config, files, contact_server)

    log.info('Done!')


def _get_product_config(context, android_product):
    try:
        products = context.config['products']
    except KeyError:
        raise ConfigValidationError('"products" is not part of the configuration')

    matching_products = [product for product in products if android_product in product['product_names']]

    if len(matching_products) == 0:
        raise TaskVerificationError('Android "{}" does not exist in the configuration of this '
                                    'instance. Are you sure you allowed to push such an '
                                    'APK?'.format(android_product))

    if len(matching_products) > 1:
        raise TaskVerificationError('The configuration is invalid: multiple product configs match '
                                    'the product "{}"'.format(android_product))

    return matching_products[0]


def _log_warning_forewords(contact_google_play, task_payload):
    if contact_google_play:
        if publish.should_commit_transaction(task_payload):
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
