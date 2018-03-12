#!/usr/bin/env python3
""" Push Snap Script main script
"""
from scriptworker import client

from pushsnapscript import artifacts


async def async_main(context):
    context.task = client.get_task(context.config)

    # TODO Sanity checks on the file
    snap_file_path = artifacts.get_snap_file_path(context)
    print(snap_file_path)


__name__ == '__main__' and client.sync_main(async_main)
