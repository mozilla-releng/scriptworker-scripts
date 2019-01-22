import logging

from scriptworker.exceptions import TaskVerificationError
from scriptworker.utils import get_single_item_from_sequence

from pushapkscript.exceptions import ConfigValidationError
from pushapkscript.task import extract_android_product_from_scopes

log = logging.getLogger(__name__)

_AUTHORIZED_PRODUCTS_TO_REACH_GOOGLE_PLAY = ('aurora', 'beta', 'release', 'fenix', 'focus', 'reference-browser')
_DEFAULT_TRACK_VALUES = ['production', 'beta', 'alpha', 'rollout', 'internal']
_EXPECTED_L10N_STRINGS_FILE_NAME = 'public/google_play_strings.json'


def publish_to_googleplay(context, apks, google_play_strings_path=None):
    from mozapkpublisher.push_apk import PushAPK
    push_apk = PushAPK(config=craft_push_apk_config(
        context, apks, google_play_strings_path,
    ))
    push_apk.run()


def craft_push_apk_config(context, apks, google_play_strings_path=None):
    android_product = extract_android_product_from_scopes(context)
    product_config = _get_product_config(context, android_product)
    valid_track_values = craft_valid_track_values(product_config['has_nightly_track'])
    payload = context.task['payload']
    track = payload['google_play_track']

    if track not in valid_track_values:
        raise TaskVerificationError('Track name "{}" not valid. Allowed values: {}'.format(track, valid_track_values))

    push_apk_config = {
        '*args': sorted(apks),   # APKs have been positional arguments since mozapkpublisher 0.6.0
        'commit': should_commit_transaction(context),
        'credentials': product_config['certificate'],
        'service_account': product_config['service_account'],
        'track': payload['google_play_track']
    }

    if product_config.get('skip_checks_fennec'):
        push_apk_config['skip_checks_fennec'] = True

    if product_config.get('skip_check_ordered_version_codes'):
        push_apk_config['skip_check_ordered_version_codes'] = True

    if product_config.get('skip_check_multiple_locales'):
        push_apk_config['skip_check_multiple_locales'] = True

    if product_config.get('skip_check_same_locales'):
        push_apk_config['skip_check_same_locales'] = True

    if not is_allowed_to_push_to_google_play(context):
        push_apk_config['do_not_contact_google_play'] = True

    if payload.get('rollout_percentage'):
        push_apk_config['rollout_percentage'] = payload['rollout_percentage']

    if product_config.get('skip_check_package_names'):
        push_apk_config['skip_check_package_names'] = True
    else:
        push_apk_config['expected_package_names'] = product_config['expected_package_names']

    if google_play_strings_path is None:
        push_apk_config['no_gp_string_update'] = True
    else:
        push_apk_config['update_gp_strings_from_file'] = google_play_strings_path

    return push_apk_config


def craft_valid_track_values(has_nightly_track):
    return _DEFAULT_TRACK_VALUES + (['nightly'] if has_nightly_track else [])


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


def is_allowed_to_push_to_google_play(context):
    android_product = extract_android_product_from_scopes(context)
    return android_product in _AUTHORIZED_PRODUCTS_TO_REACH_GOOGLE_PLAY


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
