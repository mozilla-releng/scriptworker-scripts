import logging

from mozapkpublisher.push_apk import push_apk, FileGooglePlayStrings, NoGooglePlayStrings
from scriptworker.exceptions import TaskVerificationError
from scriptworker.utils import get_single_item_from_sequence

log = logging.getLogger(__name__)

_DEFAULT_TRACK_VALUES = ['production', 'beta', 'alpha', 'rollout', 'internal']
_EXPECTED_L10N_STRINGS_FILE_NAME = 'public/google_play_strings.json'


def publish_to_googleplay(payload, product_config, apk_files, contact_google_play, google_play_strings_file=None):
    track = payload['google_play_track']
    valid_track_values = craft_valid_track_values(product_config.get('require_track'),
                                                  product_config['has_nightly_track'])
    if track not in valid_track_values:
        raise TaskVerificationError('Track name "{}" not valid. Allowed values: {}'.format(track, valid_track_values))

    with open(product_config['certificate'], 'rb') as certificate:
        push_apk(
            apks=apk_files,
            service_account=product_config['service_account'],
            google_play_credentials_file=certificate,
            track=track,
            expected_package_names=product_config.get('expected_package_names'),
            skip_check_package_names=bool(product_config.get('skip_check_package_names')),
            rollout_percentage=payload.get('rollout_percentage'),  # may be None
            google_play_strings=NoGooglePlayStrings() if google_play_strings_file is None else FileGooglePlayStrings(google_play_strings_file),
            commit=should_commit_transaction(payload),
            # Only allowed to connect to Google Play if the configuration of the pushapkscript instance allows it
            contact_google_play=contact_google_play,
            skip_check_ordered_version_codes=bool(product_config.get('skip_check_ordered_version_codes')),
            skip_check_multiple_locales=bool(product_config.get('skip_check_multiple_locales')),
            skip_check_same_locales=bool(product_config.get('skip_check_same_locales')),
            skip_checks_fennec=bool(product_config.get('skip_checks_fennec')),
        )


def should_commit_transaction(task_payload):
    # Don't commit anything by default. Committed APKs can't be unpublished,
    # unless you push a newer set of APKs.
    return task_payload.get('commit', False)


def craft_valid_track_values(require_track, has_nightly_track):
    if require_track:
        return [require_track]
    else:
        return _DEFAULT_TRACK_VALUES + (['nightly'] if has_nightly_track else [])


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
