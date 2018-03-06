import logging

from scriptworker.exceptions import TaskVerificationError
from scriptworker.utils import get_single_item_from_sequence

from pushapkscript.exceptions import NoGooglePlayStringsFound
from pushapkscript.task import extract_channel

log = logging.getLogger(__name__)

# TODO Change the "aurora" scope to "nightly" so we can use the dict defined in mozapkpublisher
CHANNEL_TO_PACKAGE_NAME = {
    'aurora': 'org.mozilla.fennec_aurora',
    'beta': 'org.mozilla.firefox_beta',
    'release': 'org.mozilla.firefox',
    # dep-signing mimics Aurora
    'dep': 'org.mozilla.fennec_aurora',
}

_CHANNELS_AUTHORIZED_TO_REACH_GOOGLE_PLAY = ('aurora', 'beta', 'release')
_EXPECTED_L10N_STRINGS_FILE_NAME = 'public/google_play_strings.json'


def publish_to_googleplay(context, apks, google_play_strings_path=None, let_mozapkpublisher_download_google_play_strings=False):
    from mozapkpublisher.push_apk import PushAPK
    push_apk = PushAPK(config=craft_push_apk_config(
        context, apks, google_play_strings_path, let_mozapkpublisher_download_google_play_strings
    ))
    push_apk.run()


def craft_push_apk_config(context, apks, google_play_strings_path=None, let_mozapkpublisher_download_google_play_strings=False):
    push_apk_config = {'apk_{}'.format(apk_type): apk_path for apk_type, apk_path in apks.items()}

    channel = extract_channel(context.task)
    push_apk_config['package_name'] = get_package_name(channel)

    push_apk_config['service_account'] = get_service_account(context, channel)
    push_apk_config['credentials'] = get_certificate_path(context, channel)

    payload = context.task['payload']
    push_apk_config['track'] = payload['google_play_track']
    if payload.get('rollout_percentage'):
        push_apk_config['rollout_percentage'] = payload['rollout_percentage']

    # Only known channels are allowed to connect to Google Play
    if not is_allowed_to_push_to_google_play(context):
        push_apk_config['do_not_contact_google_play'] = True

    if google_play_strings_path is None:
        if let_mozapkpublisher_download_google_play_strings:
            # TODO: Remove this special case once Firefox 59 reaches mozilla-release.
            # It allows older trees (that don't have a task to fetch GP strings) to fetch
            # strings in the push-apk job
            push_apk_config['update_gp_strings_from_l10n_store'] = True
        else:
            push_apk_config['no_gp_string_update'] = True
    else:
        push_apk_config['update_gp_strings_from_file'] = google_play_strings_path

    push_apk_config['commit'] = should_commit_transaction(context)

    return push_apk_config


def get_package_name(channel):
    return CHANNEL_TO_PACKAGE_NAME[channel]


def get_service_account(context, channel):
    return _get_play_config(context, channel)['service_account']


def get_certificate_path(context, channel):
    return _get_play_config(context, channel)['certificate']


def _get_play_config(context, channel):
    try:
        accounts = context.config['google_play_accounts']
    except KeyError:
        raise TaskVerificationError('"google_play_accounts" is not part of the configuration')

    try:
        return accounts[channel]
    except KeyError:
        raise TaskVerificationError('Channel "{}" does not exist in the configuration of this instance.\
    Are you sure you allowed to push such APK?'.format(channel))


def is_allowed_to_push_to_google_play(context):
    channel = extract_channel(context.task)
    return channel in _CHANNELS_AUTHORIZED_TO_REACH_GOOGLE_PLAY


def should_commit_transaction(context):
    payload = context.task['payload']
    # TODO: Stop supporting the dry_run when Firefox 59 reaches mozilla-release
    if 'dry_run' in payload and 'commit' in payload:
        raise TaskVerificationError('Payload cannot contain both "dry_run" and "commit" flags')

    try:
        return not payload['dry_run']
    except KeyError:
        # Don't commit anything by default. Committed APKs can't be unpublished,
        # unless you push a newer set of APKs.
        return payload.get('commit', False)


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

    # TODO: Modify get_single_item_from_sequence to support 2 ErrorClasses
    try:
        return get_single_item_from_sequence(
            all_paths,
            condition=lambda path: path.endswith(_EXPECTED_L10N_STRINGS_FILE_NAME),
            ErrorClass=TaskVerificationError,
            no_item_error_message='Could not find "{}" in upstreamArtifacts: {}'.format(
                _EXPECTED_L10N_STRINGS_FILE_NAME, artifact_dict
            ),
            too_many_item_error_message='"{}" is defined too many times among these upstreamArtifacts {}'.format(
                _EXPECTED_L10N_STRINGS_FILE_NAME, artifact_dict
            ),
        )
    except TaskVerificationError as e:
        if 'Could not find "' in str(e):
            raise NoGooglePlayStringsFound(_EXPECTED_L10N_STRINGS_FILE_NAME, artifact_dict)
        raise
