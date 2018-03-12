#!/usr/bin/env python3
""" Push Snap Script main script
"""
from scriptworker import client

from pushsnapscript import artifacts, snap_store, task


async def async_main(context):
    context.task = client.get_task(context.config)

    # TODO Sanity checks on the file
    snap_file_path = artifacts.get_snap_file_path(context)
    channel = task.pluck_channel(context.task)
    snap_store.push(context, snap_file_path, channel)


__name__ == '__main__' and client.sync_main(async_main)
