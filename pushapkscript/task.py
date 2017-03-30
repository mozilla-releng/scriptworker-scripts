import json
import logging

import scriptworker.client
from pushapkscript.exceptions import TaskVerificationError


log = logging.getLogger(__name__)


GOOGLE_PLAY_SCOPE_PREFIX = 'project:releng:googleplay:'
SUPPORTED_CHANNELS = ('aurora', 'beta', 'release')


def extract_channel(task):
    channels = [
        s[len(GOOGLE_PLAY_SCOPE_PREFIX):]
        for s in task['scopes']
        if s.startswith(GOOGLE_PLAY_SCOPE_PREFIX)
    ]

    log.info('Channel: %s', channels)
    if len(channels) != 1:
        raise TaskVerificationError('Only one channel can be used')

    channel = channels[0]
    if channel not in SUPPORTED_CHANNELS:
        raise TaskVerificationError(
            '"{}" is not a supported channel. Value must be in {}'. format(channel, SUPPORTED_CHANNELS)
        )

    return channel


def validate_task_schema(context):
    with open(context.config['schema_file']) as fh:
        task_schema = json.load(fh)
    log.debug(task_schema)
    scriptworker.client.validate_json_schema(context.task, task_schema)
