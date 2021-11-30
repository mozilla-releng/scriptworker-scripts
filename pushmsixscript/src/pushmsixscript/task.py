from scriptworker_client.exceptions import TaskVerificationError

MSIX_SCOPES_PREFIX = "project:releng:microsoftstore:"

_CHANNELS_AUTHORIZED_TO_REACH_MICROSOFT_STORE = ("beta", "release")
ALLOWED_CHANNELS = ("mock", *_CHANNELS_AUTHORIZED_TO_REACH_MICROSOFT_STORE)


def get_msix_channel(config, task):
    payload = task["payload"]
    if "channel" not in payload:
        raise TaskVerificationError(f"channel must be defined in the task payload. Given payload: {payload}")

    channel = payload["channel"]
    scope = MSIX_SCOPES_PREFIX + channel.split("/")[0]
    if config["push_to_store"] and scope not in task["scopes"]:
        raise TaskVerificationError(f"Channel {channel} not allowed, missing scope {scope}")

    if channel not in ALLOWED_CHANNELS:
        raise TaskVerificationError('Channel "{}" is not allowed. Allowed ones are: {}'.format(channel, ALLOWED_CHANNELS))

    return channel


def is_allowed_to_push_to_microsoft_store(config, channel):
    return config["push_to_store"] and channel in _CHANNELS_AUTHORIZED_TO_REACH_MICROSOFT_STORE
