import logging

from scriptworker.exceptions import TaskVerificationError
from scriptworker.utils import get_single_item_from_sequence

from pushapkscript.task import extract_android_product_from_scopes

log = logging.getLogger(__name__)

_AUTHORIZED_PRODUCTS_TO_REACH_GOOGLE_PLAY = ('aurora', 'beta', 'release', 'focus')
_EXPECTED_L10N_STRINGS_FILE_NAME = 'public/google_play_strings.json'


def publish_to_googleplay(context, apks, google_play_strings_path=None):
    from mozapkpublisher.push_apk import PushAPK
    push_apk = PushAPK(config=craft_push_apk_config(
        context, apks, google_play_strings_path,
    ))
    push_apk.run()


def craft_push_apk_config(context, apks, google_play_strings_path=None):
    android_product = extract_android_product_from_scopes(context)
    payload = context.task['payload']

    push_apk_config = {
        '*args': sorted(apks),   # APKs have been positional arguments since mozapkpublisher 0.6.0
        'commit': should_commit_transaction(context),
        'credentials': get_certificate_path(context, android_product),
        'service_account': get_service_account(context, android_product),
        'track': payload['google_play_track'],
    }

    if payload.get('rollout_percentage'):
        push_apk_config['rollout_percentage'] = payload['rollout_percentage']

    # Only known android_products are allowed to connect to Google Play
    if not is_allowed_to_push_to_google_play(context):
        push_apk_config['do_not_contact_google_play'] = True

    if google_play_strings_path is None:
        push_apk_config['no_gp_string_update'] = True
    else:
        push_apk_config['update_gp_strings_from_file'] = google_play_strings_path

    return push_apk_config


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
        log.warn("Google Play strings not found. Listings and what's new section won't be updated")
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
