import logging

from mozapkpublisher.push_apk import push_apk, FileGooglePlayStrings, NoGooglePlayStrings
from scriptworker.exceptions import TaskVerificationError
from scriptworker.utils import get_single_item_from_sequence
from pushapkscript.task import extract_android_product_from_scopes

log = logging.getLogger(__name__)

_EXPECTED_L10N_STRINGS_FILE_NAME = 'public/google_play_strings.json'


def publish_to_googleplay(context, apk_files, google_play_strings_file=None):
    android_product = extract_android_product_from_scopes(context)
    payload = context.task['payload']

    with open(get_certificate_path(context, android_product), 'rb') as certificate:
        push_apk(
            apks=apk_files,
            service_account=get_service_account(context, android_product),
            google_play_credentials_file=certificate,
            track=payload['google_play_track'],
            rollout_percentage=payload.get('rollout_percentage'),  # may be None
            google_play_strings=NoGooglePlayStrings() if google_play_strings_file is None else FileGooglePlayStrings(google_play_strings_file),
            commit=should_commit_transaction(context),
            # Only allowed to connect to Google Play if the configuration of the pushapkscript instance allows it
            contact_google_play=not context.config.get('do_not_contact_google_play')
        )


def get_service_account(context, android_product):
    return _get_play_config(context, android_product)['service_account']


def get_certificate_path(context, android_product):
    return _get_play_config(context, android_product)['certificate']


def _get_play_config(context, android_product):
    try:
        accounts = context.config['google_play_accounts']
    except KeyError:
        raise TaskVerificationError('"google_play_accounts" is not part of the configuration')

    try:
        return accounts[android_product]
    except KeyError:
        raise TaskVerificationError('Android "{}" does not exist in the configuration of this instance.\
    Are you sure you allowed to push such APK?'.format(android_product))


def should_commit_transaction(context):
    # Don't commit anything by default. Committed APKs can't be unpublished,
    # unless you push a newer set of APKs.
    return context.task['payload'].get('commit', False)


def get_google_play_strings_path(artifacts_per_task_id, failed_artifacts_per_task_id):
    if failed_artifacts_per_task_id:
        _check_google_play_string_is_the_only_failed_task(failed_artifacts_per_task_id)
        log.warning("Google Play strings not found. Listings and what's new section won't be updated")
        return None

    path = _find_unique_google_play_strings_file_in_dict(artifacts_per_task_id)
    log.info('Using "{}" to update Google Play listings and what\'s new section.'.format(path))
    return path


def _check_google_play_string_is_the_only_failed_task(failed_artifacts_per_task_id):
    if len(failed_artifacts_per_task_id) > 1:
        raise TaskVerificationError(
            'Only 1 task is allowed to fail. Found: {}'.format(failed_artifacts_per_task_id.keys())
        )

    task_id = list(failed_artifacts_per_task_id.keys())[0]
    failed_artifacts = failed_artifacts_per_task_id[task_id]
    if _EXPECTED_L10N_STRINGS_FILE_NAME not in failed_artifacts:
        raise TaskVerificationError(
            'Could not find "{}" in the only failed taskId "{}". Please note this is the only \
            artifact allowed to be absent. Found: {}'
            .format(_EXPECTED_L10N_STRINGS_FILE_NAME, task_id, failed_artifacts)
        )


def _find_unique_google_play_strings_file_in_dict(artifact_dict):
    all_paths = [
        path for paths in artifact_dict.values() for path in paths
    ]

    return get_single_item_from_sequence(
        all_paths,
        condition=lambda path: path.endswith(_EXPECTED_L10N_STRINGS_FILE_NAME),
        ErrorClass=TaskVerificationError,
        no_item_error_message='Could not find "{}" in upstreamArtifacts: {}'.format(_EXPECTED_L10N_STRINGS_FILE_NAME, artifact_dict),
        too_many_item_error_message='"{}" is defined too many times among these upstreamArtifacts {}'.format(_EXPECTED_L10N_STRINGS_FILE_NAME, artifact_dict),
    )
