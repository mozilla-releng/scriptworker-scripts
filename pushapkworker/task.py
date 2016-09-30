import asyncio
from copy import deepcopy
import json
import logging
import os

import scriptworker.client
from scriptworker.utils import retry_async
from pushapkworker.exceptions import TaskVerificationError
from pushapkworker.utils import raise_future_exceptions


log = logging.getLogger(__name__)


GOOGLE_PLAY_SCOPE_PREFIX = 'project:releng:googleplay:'


def extract_channel(task):
    channels = [
        s[len(GOOGLE_PLAY_SCOPE_PREFIX):]
        for s in task['scopes']
        if s.startswith(GOOGLE_PLAY_SCOPE_PREFIX)
    ]
    log.info('Channel: %s', channels)
    if len(channels) != 1:
        raise TaskVerificationError('Only one channel can be used')
    return channels[0]


def validate_task_schema(context):
    with open(context.config['schema_file']) as fh:
        task_schema = json.load(fh)
    log.debug(task_schema)
    scriptworker.client.validate_json_schema(context.task, task_schema)


async def download_files(context):
    payload = context.task['payload']
    apks_to_download = payload['apks']
    work_dir = context.config['work_dir']

    tasks = []
    files = {}
    download_config = deepcopy(context.config)
    download_config.setdefault('valid_artifact_task_ids', context.task['dependencies'])
    for apk_type, apk_url in apks_to_download.items():
        rel_path = scriptworker.client.validate_artifact_url(download_config, apk_url)
        abs_file_path = os.path.join(work_dir, rel_path)
        files[apk_type] = abs_file_path

        # XXX download_file() is imported here, in order to patch it.
        # This is due to retry_async() taking it as an argument
        from pushapkworker.utils import download_file
        tasks.append(
            asyncio.ensure_future(
                retry_async(download_file, args=(context, apk_url, abs_file_path))
            )
        )

    await raise_future_exceptions(tasks)
    tasks = []
    return files
