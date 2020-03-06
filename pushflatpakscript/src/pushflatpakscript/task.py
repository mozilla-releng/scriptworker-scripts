from scriptworker.exceptions import TaskVerificationError

FLATPAK_SCOPES_PREFIX = "project:releng:flathub:firefox:"

_CHANNELS_AUTHORIZED_TO_REACH_FLATHUB = ("beta", "stable")
ALLOWED_CHANNELS = ("mock", *_CHANNELS_AUTHORIZED_TO_REACH_FLATHUB)


def get_flatpak_channel(config, task):
    payload = task["payload"]
    if "channel" not in payload:
        raise TaskVerificationError(f"channel must be defined in the task payload. Given payload: {payload}")

    channel = payload["channel"]
    scope = FLATPAK_SCOPES_PREFIX + channel
    # TODO: uncomment this section once try staging is done
    # if config["push_to_flathub"] and scope not in task["scopes"]:
        # raise TaskVerificationError(f"Channel {channel} not allowed, missing scope {scope}")

    if channel not in ALLOWED_CHANNELS:
        raise TaskVerificationError('Channel "{}" is not allowed. Allowed ones are: {}'.format(channel, ALLOWED_CHANNELS))

    return channel


def is_allowed_to_push_to_flathub(config, channel):
    return "push_to_flathub" in config and config["push_to_flathub"] and channel in _CHANNELS_AUTHORIZED_TO_REACH_FLATHUB
