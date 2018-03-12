from scriptworker.exceptions import TaskVerificationError
from scriptworker.utils import get_single_item_from_sequence

SNAP_SCOPES_PREFIX = 'project:releng:snapcraft:firefox:'
ALLOWED_CHANNELS = ('edge', 'candidate')


def pluck_channel(task):
    scope = get_single_item_from_sequence(
        task['scopes'],
        lambda scope: scope.startswith(SNAP_SCOPES_PREFIX),
        ErrorClass=TaskVerificationError,
        no_item_error_message='No scope starts with {}'.format(SNAP_SCOPES_PREFIX),
        too_many_item_error_message='Too many scopes start with {}'.format(SNAP_SCOPES_PREFIX),
    )

    channel = scope[len(SNAP_SCOPES_PREFIX):]

    if channel not in ALLOWED_CHANNELS:
        raise TaskVerificationError(
            'Channel "{}" is not allowed. Allowed ones are: {}'.format(channel, ALLOWED_CHANNELS)
        )

    return channel
