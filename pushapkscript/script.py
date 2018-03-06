#!/usr/bin/env python3
""" PushAPK main script
"""
import logging

from scriptworker.artifacts import get_upstream_artifacts_full_paths_per_task_id
from scriptworker.client import get_task, sync_main

from pushapkscript import jarsigner
from pushapkscript.apk import sort_and_check_apks_per_architectures
from pushapkscript.exceptions import NoGooglePlayStringsFound
from pushapkscript.googleplay import publish_to_googleplay, should_commit_transaction, \
    is_allowed_to_push_to_google_play, get_google_play_strings_path
from pushapkscript.task import validate_task_schema, extract_channel


log = logging.getLogger(__name__)


async def async_main(context):
    logging.getLogger('oauth2client').setLevel(logging.WARNING)

    context.task = get_task(context.config)
    _log_warning_forewords(context)

    log.info('Validating task definition...')
    validate_task_schema(context)

    log.info('Verifying upstream artifacts...')
    artifacts_per_task_id, failed_artifacts_per_task_id = get_upstream_artifacts_full_paths_per_task_id(context)

    all_apks = [
        artifact
        for artifacts_list in artifacts_per_task_id.values()
        for artifact in artifacts_list
        if artifact.endswith('.apk')
    ]
    apks_per_architectures = sort_and_check_apks_per_architectures(
        all_apks, channel=extract_channel(context.task)
    )

    log.info('Verifying APKs\' signatures...')
    [jarsigner.verify(context, apk_path) for apk_path in apks_per_architectures.values()]

    log.info('Finding whether Google Play strings can be updated...')
    try:
        google_play_strings_path = get_google_play_strings_path(artifacts_per_task_id, failed_artifacts_per_task_id)
        let_mozapkpublisher_download_google_play_strings = False
    except NoGooglePlayStringsFound:
        # TODO: Remove this special catch once Firefox 59 reaches mozilla-release.
        # It allows older trees (that don't have a task to fetch GP strings) to fetch
        # strings in the push-apk job
        log.warn('No Google Play string task defined in upstreamArtifacts. This is considered as a legacy task definition.\
This behavior is deprecated and will be removed after Firefox 59 reaches mozilla-release.')
        google_play_strings_path = None
        let_mozapkpublisher_download_google_play_strings = True

    log.info('Delegating publication to mozapkpublisher...')
    publish_to_googleplay(
        context, apks_per_architectures, google_play_strings_path,
        let_mozapkpublisher_download_google_play_strings
    )

    log.info('Done!')


def _log_warning_forewords(context):
    if is_allowed_to_push_to_google_play(context):
        if should_commit_transaction(context):
            log.warn('You will publish APKs to Google Play. This action is irreversible,\
if no error is detected either by this script or by Google Play.')
        else:
            log.warn('APKs will be submitted to Google Play, but no change will not be committed.')
    else:
        log.warn('You do not have the rights to reach Google Play. *All* requests will be mocked.')


__name__ == '__main__' and sync_main(async_main)
