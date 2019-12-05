from scriptworker.exceptions import TaskVerificationError
from scriptworker.utils import get_single_item_from_sequence

SNAP_SCOPES_PREFIX = "project:releng:snapcraft:firefox:"

_CHANNELS_AUTHORIZED_TO_REACH_SNAP_STORE = ("beta", "candidate", "esr/stable", "esr/candidate")
ALLOWED_CHANNELS = ("mock", *_CHANNELS_AUTHORIZED_TO_REACH_SNAP_STORE)


def get_snap_channel(config, task):
    if "channel" in task["payload"]:
        channel = task["payload"]["channel"]
        scope = SNAP_SCOPES_PREFIX + channel.split("/")[0]
        if config["push_to_store"] and scope not in task["scopes"]:
            raise TaskVerificationError(f"Channel {channel} not allowed, missing scope {scope}")
    else:
        scope = get_single_item_from_sequence(
            task["scopes"],
            lambda scope: scope.startswith(SNAP_SCOPES_PREFIX),
            ErrorClass=TaskVerificationError,
            no_item_error_message="No scope starts with {}".format(SNAP_SCOPES_PREFIX),
            too_many_item_error_message="Too many scopes start with {}".format(SNAP_SCOPES_PREFIX),
        )
        channel = scope[len(SNAP_SCOPES_PREFIX) :]
        channel = "esr/stable" if channel == "esr" else channel

    if channel not in ALLOWED_CHANNELS:
        raise TaskVerificationError('Channel "{}" is not allowed. Allowed ones are: {}'.format(channel, ALLOWED_CHANNELS))

    return channel


def is_allowed_to_push_to_snap_store(config, channel):
    return config["push_to_store"] and channel in _CHANNELS_AUTHORIZED_TO_REACH_SNAP_STORE
