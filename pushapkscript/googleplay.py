from pushapkscript.exceptions import TaskVerificationError
from pushapkscript.task import extract_channel

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


def publish_to_googleplay(context, apks, google_play_strings_path=None):
    from mozapkpublisher.push_apk import PushAPK
    push_apk = PushAPK(config=craft_push_apk_config(context, apks, google_play_strings_path))
    push_apk.run()


def craft_push_apk_config(context, apks, google_play_strings_path=None):
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
        return None

    return _find_unique_google_play_strings_file_in_dict(artifacts_per_task_id)


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
    l10n_strings_paths = [
        path
        for task_id, paths in artifact_dict.items()
        for path in paths
        if _EXPECTED_L10N_STRINGS_FILE_NAME in path
    ]

    number_of_artifacts_found = len(l10n_strings_paths)
    if number_of_artifacts_found == 0:
        raise TaskVerificationError(
            'Could not find "{}" in upstreamArtifacts: {}'.format(_EXPECTED_L10N_STRINGS_FILE_NAME, artifact_dict)
        )
    if number_of_artifacts_found > 1:
        raise TaskVerificationError(
            'More than one artifact "{}" found in upstreamArtifacts: {}'
            .format(_EXPECTED_L10N_STRINGS_FILE_NAME, l10n_strings_paths)
        )

    return l10n_strings_paths[0]
