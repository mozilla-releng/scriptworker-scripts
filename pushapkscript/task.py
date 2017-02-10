import json
import logging
import os

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


async def download_files(context):
    apks_to_download = context.task['payload']['apks']
    work_dir = context.config['work_dir']

    apks_to_process = {apk_type: {'url': apk_url, 'target_dir': os.path.join(work_dir, apk_type)} for apk_type, apk_url in apks_to_download.items()}

    downloaded_files = {}
    # XXX download_artifacts() is imported here, in order to patch it
    from scriptworker.artifacts import download_artifacts
    for apk_type, values in apks_to_process.items():
        # TODO: Use a dict comprehension once Python 3.6 is supported by scriptworker
        # https://github.com/mozilla-releng/scriptworker/issues/47
        downloaded_files[apk_type] = await download_artifacts(context, file_urls=[values['url']], parent_dir=values['target_dir'])

    return {
        apk_type: locations[0] for apk_type, locations in downloaded_files.items()
    }
