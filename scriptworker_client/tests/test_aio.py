#!/usr/bin/env python
# coding=utf-8
"""Test scriptworker_client.aio
"""
import aiohttp
import asyncio
from async_generator import asynccontextmanager
from datetime import datetime
import mock
import os
import pytest
import re
import shutil
import time
import scriptworker_client.aio as aio
from scriptworker_client.exceptions import (
    Download404,
    DownloadError,
    RetryError,
    TaskError,
    TimeoutError,
)


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
    return int("{}{}".format(int(time.time()), str(datetime.now().microsecond)[0:4]))


class FakeSession:
    """Aiohttp session mock."""

    statuses = None
    content = [b"first", b"second", None]

    @asynccontextmanager
    async def request(self, method, url, **kwargs):
        """Fake request. "url" should be a comma-delimited set of integers
        that we'll use for status.

        """

        async def _fake_text():
            return method

        async def _fake_json():
            return {"method": method}

        async def _fake_content_read(*args, **kwargs):
            return self.content.pop(0)

        if not self.statuses:
            self.statuses = url.split(",")
        resp = mock.MagicMock()
        resp.status = int(self.statuses.pop(0))
        resp.text = _fake_text
        resp.json = _fake_json
        # Fake download: will give `firstsecond`
        content = mock.MagicMock()
        content.read = _fake_content_read
        resp.content = content
        # Fake history for _log_download_error
        history = mock.MagicMock()
        history.status = resp.status
        history.text = _fake_text
        resp.history = [history, history]

        yield resp

    @asynccontextmanager
    async def get(self, url, **kwargs):
        async with self.request("get", url, **kwargs) as resp:
            yield resp


@asynccontextmanager
async def GetFakeSession(*args, **kwargs):
    """Helper class to replace ``aiohttp.ClientSession()``

    """
    yield FakeSession()


async def noop_async(*args, **kwargs):
    """Noop coroutine."""


# raise_future_exceptions {{{1
@pytest.mark.parametrize(
    "coroutines,expected,raises,timeout",
    (
        ([succeed(0), succeed(1)], [0, 1], False, None),
        ([succeed(0), fail()], None, TaskError, None),
        ([succeed(0, sleep_time=2), succeed(1, sleep_time=3)], None, TimeoutError, 0.1),
        ([], None, False, None),
    ),
)
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
        asyncio.ensure_future(aio.semaphore_wrapper(sem, async_time(sleep_time=0.1))),
        asyncio.ensure_future(aio.semaphore_wrapper(sem, async_time(sleep_time=0.1))),
        asyncio.ensure_future(aio.semaphore_wrapper(sem, async_time(sleep_time=0.1))),
        asyncio.ensure_future(aio.semaphore_wrapper(sem, async_time(sleep_time=0.1))),
    ]
    with pytest.raises(TimeoutError):
        await aio.raise_future_exceptions(futures, timeout=0.15)
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
@pytest.mark.parametrize("attempt", (0, 1, 2, 3, 4, 5))
def test_calculate_sleep_time(attempt):
    """The sleep time for attempt number ``attempt`` is between ``min_delay``
    and ``max_delay``.

    """
    delay_factor = 0.1
    randomization_factor = 0.25
    max_delay = 2
    if attempt == 0:
        min_delay = max_delay = 0
    else:
        min_delay = (float(2 ** (attempt - 1)) * float(delay_factor)) * (
            (randomization_factor * -1) + 1
        )
        max_delay = min(
            max_delay,
            (float(2 ** (attempt - 1)) * float(delay_factor))
            * ((randomization_factor * 1) + 1),
        )
    t = aio.calculate_sleep_time(
        attempt,
        delay_factor=delay_factor,
        randomization_factor=randomization_factor,
        max_delay=max_delay,
    )
    assert min_delay <= t <= max_delay


retry_count = {}


async def fail_first(*args, **kwargs):
    global retry_count
    retry_count["fail_first"] += 1
    if retry_count["fail_first"] < 2:
        raise TaskError("first")
    return "yay"


async def always_fail(*args, **kwargs):
    global retry_count
    retry_count.setdefault("always_fail", 0)
    retry_count["always_fail"] += 1
    raise TaskError("fail")


async def fake_sleep(*args, **kwargs):
    pass


@pytest.mark.asyncio
async def test_retry_async_fail_first():
    """``retry_async`` retries if the first attempt fails.

    """
    global retry_count
    retry_count["fail_first"] = 0
    status = await aio.retry_async(fail_first, sleeptime_kwargs={"delay_factor": 0})
    assert status == "yay"
    assert retry_count["fail_first"] == 2


@pytest.mark.asyncio
async def test_retry_async_always_fail():
    """``retry_async`` gives up if we fail the max number of attempts.

    """
    global retry_count
    retry_count["always_fail"] = 0
    with mock.patch("asyncio.sleep", new=fake_sleep):
        with pytest.raises(TaskError):
            status = await aio.retry_async(
                always_fail, sleeptime_kwargs={"delay_factor": 0}
            )
            assert status is None
    assert retry_count["always_fail"] == 5


# request {{{1
@pytest.mark.parametrize(
    "url,method,return_type,expected,exception,num_attempts",
    (
        ("200", "expected", "text", "expected", None, 1),
        ("200", "expected", "json", {"method": "expected"}, None, 1),
        ("200", "expected", "response", "expected", None, 1),
        ("500,200", "expected", "text", "expected", None, 3),
        ("500", "expected", "text", "expected", RetryError, 2),
        ("404", "expected", "text", "expected", TaskError, 1),
    ),
)
@pytest.mark.asyncio
async def test_request(
    mocker, url, method, return_type, expected, exception, num_attempts
):
    """A request returns the expected value, or raises ``exception`` if not ``None``.

    """
    mocker.patch.object(aiohttp, "ClientSession", new=GetFakeSession)
    mocker.patch.object(asyncio, "sleep", new=noop_async)

    if not exception:
        result = await aio.request(
            url, method=method, return_type=return_type, num_attempts=num_attempts
        )
        if return_type in ("text", "json"):
            assert result == expected
        else:
            assert await result.text() == expected
    else:
        with pytest.raises(exception):
            await aio.request(
                url, method=method, return_type=return_type, num_attempts=num_attempts
            )


# download_file {{{1
@pytest.mark.parametrize(
    "url,expected,raises",
    (
        ("200", "firstsecond", False),
        ("404", None, Download404),
        ("500", None, DownloadError),
    ),
)
@pytest.mark.asyncio
async def test_download_file(tmpdir, url, expected, raises, mocker):
    mocker.patch.object(aiohttp, "ClientSession", new=GetFakeSession)
    path = os.path.join(tmpdir, "foo")
    if raises:
        with pytest.raises(raises):
            await aio.download_file(url, path)
    else:
        await aio.download_file(url, path)
        with open(path, "r") as fh:
            contents = fh.read()
        assert contents == expected
