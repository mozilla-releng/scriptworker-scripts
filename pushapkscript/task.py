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
    payload = context.task['payload']
    apks_to_download = payload['apks']

    # XXX: download_artifacts() takes a list of urls. In order to not loose the association between
    # an apk_type and an apk_url, we set an order once and for all.
    # Warning: This relies on download_artifacts() not changing the order of the files
    ordered_apks = [(apk_type, apk_url) for apk_type, apk_url in apks_to_download.items()]
    file_urls = [apk_url for _, apk_url in ordered_apks]

    # XXX download_artifacts() is imported here, in order to patch it
    from scriptworker.task import download_artifacts
    ordered_files = await download_artifacts(context, file_urls)

    files = {}
    work_dir = context.config['work_dir']
    for i in range(0, len(ordered_apks)):
        apk_type = ordered_apks[i][0]
        apk_relative_path = ordered_files[i]
        files[apk_type] = os.path.join(work_dir, apk_relative_path)

    return files
