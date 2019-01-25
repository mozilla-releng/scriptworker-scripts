#!/usr/bin/env python3
""" PushAPK main script
"""
import logging
import os

from scriptworker import client, artifacts

from pushapkscript import googleplay, jarsigner, task, manifest


log = logging.getLogger(__name__)


async def async_main(context):
    logging.getLogger('oauth2client').setLevel(logging.WARNING)
    _log_warning_forewords(context)

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
        manifest.verify(context, apk_path)

    if task.extract_android_product_from_scopes(context) in ['fenix', 'focus', 'reference-browser']:
        log.warning('This product does not upload strings automatically. Skipping Google Play strings search.')
        google_play_strings_path = None
    else:
        log.info('Finding whether Google Play strings can be updated...')
        google_play_strings_path = googleplay.get_google_play_strings_path(
            artifacts_per_task_id, failed_artifacts_per_task_id
        )

    log.info('Delegating publication to mozapkpublisher...')
    googleplay.publish_to_googleplay(
        context, all_apks_paths, google_play_strings_path,
    )

    log.info('Done!')


def _log_warning_forewords(context):
    if not context.config.get('do_not_contact_google_play'):
        if googleplay.should_commit_transaction(context):
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
