#!/usr/bin/env python3
""" PushAPK main script
"""
import logging
import os

from scriptworker import client, artifacts

from pushapkscript import googleplay, jarsigner, task


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
    [jarsigner.verify(context, apk_path) for apk_path in all_apks_paths]

    if task.extract_android_product_from_scopes(context) == 'focus':
        log.warn('Focus does not upload strings automatically. Skipping Google Play strings search.')
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
    if googleplay.is_allowed_to_push_to_google_play(context):
        if googleplay.should_commit_transaction(context):
            log.warn('You will publish APKs to Google Play. This action is irreversible,\
if no error is detected either by this script or by Google Play.')
        else:
            log.warn('APKs will be submitted to Google Play, but no change will not be committed.')
    else:
        log.warn('You do not have the rights to reach Google Play. *All* requests will be mocked.')


def get_default_config():
    cwd = os.getcwd()
    parent_dir = os.path.dirname(cwd)

    return {
        'work_dir': os.path.join(parent_dir, 'work_dir'),
        'schema_file': os.path.join(cwd, 'pushapkscript', 'data', 'pushapk_task_schema.json'),
        'verbose': False,
    }


def main(config_path=None):
    client.sync_main(async_main, config_path=config_path, default_config=get_default_config())


__name__ == '__main__' and main()
