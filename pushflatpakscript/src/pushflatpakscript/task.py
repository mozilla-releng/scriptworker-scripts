from scriptworker.exceptions import TaskVerificationError

_CHANNELS_AUTHORIZED_TO_REACH_FLATHUB = ("beta", "stable")
ALLOWED_CHANNELS = ("mock", *_CHANNELS_AUTHORIZED_TO_REACH_FLATHUB)


def get_flatpak_channel(config, task):
    payload = task["payload"]
    if "channel" not in payload:
        raise TaskVerificationError(f"Channel must be defined in the task payload. Given payload: {payload}")

    channel = payload["channel"]
    legacy_scope = f"{config['taskcluster_scope_prefix']}{channel}"
    scope_prefix = f"{config['taskcluster_scope_prefix']}{channel}:"
    if config["push_to_flathub"]:
        if legacy_scope not in task["scopes"] and not any(scope.startswith(scope_prefix) for scope in task["scopes"]):
            raise TaskVerificationError(f"Channel {channel} not allowed, missing scope {scope_prefix}*")

    if channel not in ALLOWED_CHANNELS:
        raise TaskVerificationError('Channel "{}" is not allowed. Allowed ones are: {}'.format(channel, ALLOWED_CHANNELS))

    return channel


def get_flatpak_app(config, task):
    channel = task["payload"]["channel"]
    scope_prefix = f"{config['taskcluster_scope_prefix']}{channel}:"
    apps = [scope.removeprefix(scope_prefix) for scope in task["scopes"] if scope.startswith(scope_prefix)]
    if len(apps) > 1:
        raise TaskVerificationError(f"Multiple app ids in task scopes, expected just one: {apps}")
    if not apps:
        return config["app_id"]
    return apps[0]


def is_allowed_to_push_to_flathub(config, channel):
    return "push_to_flathub" in config and config["push_to_flathub"] and channel in _CHANNELS_AUTHORIZED_TO_REACH_FLATHUB
