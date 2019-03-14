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


# retry_async {{{1
@pytest.mark.parametrize('attempt', (0, 1, 2, 3, 4, 5))
def test_calculate_sleep_time(attempt):
    """The sleep time for attempt number ``attempt`` is between ``min_delay``
    and ``max_delay``.

    """
    delay_factor = .1
    randomization_factor = .25
    max_delay = 2
    if attempt == 0:
        min_delay = max_delay = 0
    else:
        min_delay = (float(2 ** (attempt - 1)) * float(delay_factor)) * ((randomization_factor * -1) + 1)
        max_delay = min(
            max_delay,
            (float(2 ** (attempt - 1)) * float(delay_factor)) * ((randomization_factor * 1) + 1)
        )
    t = aio.calculate_sleep_time(
        attempt, delay_factor=delay_factor,
        randomization_factor=randomization_factor, max_delay=max_delay
    )
    assert min_delay <= t <= max_delay


retry_count = {}


async def fail_first(*args, **kwargs):
    global retry_count
    retry_count['fail_first'] += 1
    if retry_count['fail_first'] < 2:
        raise TaskError("first")
    return "yay"


async def always_fail(*args, **kwargs):
    global retry_count
    retry_count.setdefault('always_fail', 0)
    retry_count['always_fail'] += 1
    raise TaskError("fail")


async def fake_sleep(*args, **kwargs):
    pass


@pytest.mark.asyncio
async def test_retry_async_fail_first():
    """
    """
    global retry_count
    retry_count['fail_first'] = 0
    status = await aio.retry_async(fail_first, sleeptime_kwargs={'delay_factor': 0})
    assert status == "yay"
    assert retry_count['fail_first'] == 2


@pytest.mark.asyncio
async def test_retry_async_always_fail():
    global retry_count
    retry_count['always_fail'] = 0
    with mock.patch('asyncio.sleep', new=fake_sleep):
        with pytest.raises(TaskError):
            status = await aio.retry_async(
                always_fail, sleeptime_kwargs={'delay_factor': 0}
            )
            assert status is None
    assert retry_count['always_fail'] == 5
