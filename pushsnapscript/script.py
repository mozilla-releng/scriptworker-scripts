#!/usr/bin/env python3
""" Push Snap Script main script
"""
from scriptworker import client


async def async_main(context):
    context.task = client.get_task(context.config)
    print('Hello World!')


__name__ == '__main__' and client.sync_main(async_main)
