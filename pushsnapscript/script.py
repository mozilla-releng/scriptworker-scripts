#!/usr/bin/env python3
""" Push Snap Script main script
"""
import logging

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


__name__ == '__main__' and client.sync_main(async_main)
