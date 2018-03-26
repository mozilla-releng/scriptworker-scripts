#!/usr/bin/env python3
""" Push Snap Script main script
"""
import logging
import os

from scriptworker import client

from pushsnapscript import artifacts, snap_store, task

log = logging.getLogger(__name__)


async def async_main(context):
    context.task = client.get_task(context.config)
    _log_warning_forewords(context)

    # TODO Sanity checks on the file
    snap_file_path = artifacts.get_snap_file_path(context)
    channel = task.pluck_channel(context.task)
    snap_store.push(context, snap_file_path, channel)


def _log_warning_forewords(context):
    if not task.is_allowed_to_push_to_snap_store(context):
        log.warn('You do not have the rights to reach Snap store. *All* requests will be mocked.')


def get_default_config(base_dir=None):
    base_dir = base_dir or os.path.dirname(os.getcwd())
    default_config = {
        'work_dir': os.path.join(base_dir, 'work_dir'),
        'schema_file': os.path.join(os.path.dirname(__file__), 'data', 'push_snap_task_schema.json'),
        'verbose': False,
    }
    return default_config


def main(config_path=None):
    return client.sync_main(async_main, config_path=config_path, default_config=get_default_config())


__name__ == '__main__' and main()
