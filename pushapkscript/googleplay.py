from pushapkscript.task import extract_channel

# TODO Change the "aurora" scope to "nightly" so we can use the dict defined in mozapkpublisher
CHANNEL_TO_PACKAGE_NAME = {
    'aurora': 'org.mozilla.fennec_aurora',
    'beta': 'org.mozilla.firefox_beta',
    'release': 'org.mozilla.firefox',
}


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

    # Don't commit anything, by default. Committed APKs can't be unpublished, unless
    # you push a newer set of APKs.
    push_apk_config['dry_run'] = payload.get('dry_run', True)

    return push_apk_config


def get_package_name(channel):
    return CHANNEL_TO_PACKAGE_NAME[channel]


def get_service_account(context, channel):
    return _get_play_config(context, channel)['service_account']


def get_certificate_path(context, channel):
    return _get_play_config(context, channel)['certificate']


def _get_play_config(context, channel):
    return context.config['google_play_accounts'][channel]
