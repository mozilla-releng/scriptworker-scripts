#!/usr/bin/env python
# coding=utf-8
"""Test scriptworker_client.aio
"""
import asyncio
from datetime import datetime
import mock
import os
import pytest
import re
import shutil
import tempfile
import time
import scriptworker_client.aio as aio
from scriptworker_client.exceptions import RetryError, TaskError, TimeoutError


# helpers {{{1
async def fail(sleep_time=0, exception=TaskError):
    """Sleep ``sleep_time`` seconds, raise ``exception``.

    """
    await asyncio.sleep(sleep_time)
    raise exception("foo")


async def succeed(value, sleep_time=0):
    """Sleep ``sleep_time`` seconds, return ``value``.

    """
    await asyncio.sleep(sleep_time)
    return value


async def async_time(sleep_time=0):
    """Sleep ``sleep_time`` seconds, return milliseconds since epoch as an int.

    """
    await asyncio.sleep(sleep_time)
    return int("{}{}".format(
        int(time.time()), str(datetime.now().microsecond)[0:4]
    ))


# raise_future_exceptions {{{1
@pytest.mark.parametrize('coroutines,expected,raises,timeout', ((
    [
        succeed(0),
        succeed(1),
    ],
    [0, 1], False, None
), (
    [
        succeed(0),
        fail(),
    ],
    None, TaskError, None
), (
    [
        succeed(0, sleep_time=2),
        succeed(1, sleep_time=3),
    ],
    None, TimeoutError, .1
)))
@pytest.mark.asyncio
async def test_raise_future_exceptions(coroutines, expected, raises, timeout):
    """Future exceptions are raised. If there are no exceptions, the results
    are returned. Hitting a timeout should raise a ``TimeoutError``.

    """
    futures = []
    for coro in coroutines:
        futures.append(asyncio.ensure_future(coro))
    if raises:
        with pytest.raises(raises):
            await aio.raise_future_exceptions(futures, timeout=timeout)
    else:
        assert await aio.raise_future_exceptions(futures, timeout=timeout) == expected


# semaphore_wrapper {{{1
@pytest.mark.asyncio
async def test_semaphore_wrapper():
    """``semaphore_wrapper`` limits concurrency through the passed ``Semaphore``.

    """
    sem = asyncio.Semaphore(2)
    futures = [
        asyncio.ensure_future(aio.semaphore_wrapper(sem, async_time, sleep_time=.1)),
        asyncio.ensure_future(aio.semaphore_wrapper(sem, async_time, sleep_time=.1)),
        asyncio.ensure_future(aio.semaphore_wrapper(sem, async_time, sleep_time=.1)),
        asyncio.ensure_future(aio.semaphore_wrapper(sem, async_time, sleep_time=.1)),
    ]
    with pytest.raises(TimeoutError):
        await aio.raise_future_exceptions(futures, timeout=.15)
    results1 = []
    for fut in futures:
        try:
            if not fut.exception():
                results1.append(fut.result())
        except asyncio.InvalidStateError:
            pass
    assert len(results1) == 2  # only 2 futures had time to finish in .15s
    results2 = await aio.raise_future_exceptions(futures)
    assert len(results2) == 4
    assert results1 == results2[0:2]
