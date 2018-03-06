import logging

from scriptworker.exceptions import TaskVerificationError


log = logging.getLogger(__name__)


GOOGLE_PLAY_SCOPE_PREFIX = 'project:releng:googleplay:'
SUPPORTED_CHANNELS = ('aurora', 'beta', 'release', 'dep')


def extract_channel(task):
    channels = [
        s[len(GOOGLE_PLAY_SCOPE_PREFIX):]
        for s in task['scopes']
        if s.startswith(GOOGLE_PLAY_SCOPE_PREFIX)
    ]

    if len(channels) != 1:
        raise TaskVerificationError('Only one channel can be used. Channels found: {}'.format(channels))

    channel = channels[0]
    if channel not in SUPPORTED_CHANNELS:
        raise TaskVerificationError(
            '"{}" is not a supported channel. Value must be in {}'. format(channel, SUPPORTED_CHANNELS)
        )

    return channel
