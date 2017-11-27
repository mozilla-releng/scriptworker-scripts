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


def publish_to_googleplay(context, apks):
    from mozapkpublisher.push_apk import PushAPK
    push_apk = PushAPK(config=craft_push_apk_config(context, apks))
    push_apk.run()


def craft_push_apk_config(context, apks):
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

    # TODO Configure this value dynamically in Bug 1385401
    push_apk_config['update_gp_strings_from_l10n_store'] = True

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
    # Don't commit anything by default. Committed APKs can't be unpublished,
    # unless you push a newer set of APKs.
    return payload.get('commit', False)
