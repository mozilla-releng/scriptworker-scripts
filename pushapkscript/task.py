import logging

from scriptworker.exceptions import TaskVerificationError
from scriptworker.utils import get_single_item_from_sequence


log = logging.getLogger(__name__)


GOOGLE_PLAY_SCOPE_PREFIX = 'project:releng:googleplay:'
SUPPORTED_CHANNELS = ('aurora', 'beta', 'release', 'dep')


def extract_channel(task):
    scope = get_single_item_from_sequence(
        task['scopes'],
        condition=lambda scope: scope.startswith(GOOGLE_PLAY_SCOPE_PREFIX),
        ErrorClass=TaskVerificationError,
        no_item_error_message='No valid scope found. Task must have a scope that starts with "{}"'.format(GOOGLE_PLAY_SCOPE_PREFIX),
        too_many_item_error_message='More than one valid scope given',
    )

    channel = scope[len(GOOGLE_PLAY_SCOPE_PREFIX):]

    if channel not in SUPPORTED_CHANNELS:
        raise TaskVerificationError(
            '"{}" is not a supported channel. Value must be in {}'.format(channel, SUPPORTED_CHANNELS)
        )

    return channel
