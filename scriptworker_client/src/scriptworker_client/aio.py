#!/usr/bin/env python
"""Async helper functions."""
import asyncio
import fcntl
import logging
import os
import random
import sys

import aiohttp
import async_timeout

from scriptworker_client.exceptions import (
    Download404,
    DownloadError,
    LockfileError,
    RetryError,
    TaskError,
    TimeoutError,
)
from scriptworker_client.utils import makedirs, rm

if sys.version_info < (3, 7):  # pragma: no cover
    from async_generator import asynccontextmanager
else:  # pragma: no cover
    from contextlib import asynccontextmanager


log = logging.getLogger(__name__)


# raise_future_exceptions {{{1
async def raise_future_exceptions(futures, timeout=None):
    """Await a list of futures and raise any exceptions.

    Args:
        futures (list): the futures to await
        timeout (int, optional): If not ``None``, timeout after this many seconds.
            Defaults to ``None``.

    Raises:
        Exception: on error
        TimeoutError: on timeout

    Returns:
        list: the results from the futures

    """
    if not futures:
        return
    done, pending = await asyncio.wait(futures, timeout=timeout)
    if pending:
        raise TimeoutError(
            "{} futures still pending after timeout of {}".format(len(pending), timeout)
        )
    results = []
    exceptions = []
    for fut in futures:
        exc = fut.exception()
        if exc:
            exceptions.append(exc)
        else:
            results.append(fut.result())
    if exceptions:
        raise exceptions[0]
    return results


# semaphore_wrapper {{{1
async def semaphore_wrapper(semaphore, coro):
    """Wrap an async function with semaphores.

    Usage::

        semaphore = asyncio.Semaphore(10)  # max 10 concurrent
        futures = []
        futures.append(asyncio.ensure_future(semaphore_wrapper(
            semaphore, do_something(arg1, arg2, kwarg1='foo')
        )))
        await raise_future_exceptions(futures)

    Args:
        semaphore (asyncio.Semaphore): the semaphore to wrap the action with
        coro (coroutine): an asyncio coroutine

    Returns:
        the result of ``action``.

    """
    async with semaphore:
        return await coro


# lockfile {{{1
@asynccontextmanager
async def lockfile(paths, name=None, attempts=10, sleep=30):
    """Acquire a lockfile from among ``paths`` and yield the path.

    If we want inter-process semaphores, we can use lock files rather than
    ``asyncio.Semaphore``.

    The reason we're using ``open(path, "x")`` rather than purely relying
    on ``fcntl.lockf`` is that fcntl file locking doesn't lock the file
    inside the current process, only for outside processes. If we don't
    keep track of which lockfiles we've used in our async script, we can
    easily blow away our own lock if we, say, used ``open(path, "w")`` or
    ``open(path, "a") and then closed any of the open filehandles.

    (See http://0pointer.de/blog/projects/locking.html for more details.)

    Args:
        paths (list): a list of path strings to use as lockfiles.
        name (str, optional): a descriptive name for the process that needs
            the lockfile, for logging purposes. Defaults to ``None``.
        attempts (int, optional): the number of attempts to get a lockfile.
            This means we attempt to get a lockfile from every path in ``paths``, ``attempts`` times. Defaults to 20.
        sleep (int, optional): the number of seconds to sleep between attempts.
            We sleep after attempting every path in ``paths``. Defaults to 30.

    Yields:
        str: the lockfile path acquired.

    Raises:
        LockfileError: if we've exhausted our attempts.

    """
    if name is not None:
        acquired_msg = "Lockfile acquired for {} at %s".format(name)
        wait_msg = "Couldn't get lock for {}; sleeping %s".format(name)
        failed_msg = "Can't get lock for {} from paths %s after %s attempts".format(
            name
        )
    else:
        acquired_msg = "Lockfile acquired at %s"
        wait_msg = "Couldn't get lock; sleeping %s"
        failed_msg = "Can't get lock from paths %s after %s attempts"
    for attempt in range(0, attempts):
        for path in [item for item in random.sample(paths, len(paths))]:
            try:
                # Ensure the file doesn't exist, so we don't blow away
                # our own lockfiles.
                with open(path, "x") as fh:
                    # Acquire an fcntl lock, in case other processes
                    # use something other than ``lockfile`` to acquire
                    # locks
                    try:
                        fcntl.lockf(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        log.debug(acquired_msg, path)
                        yield path
                        # We'll clean up `path` in the `finally` block below
                        return
                    finally:
                        rm(path)
            except (FileExistsError, OSError):
                continue
        log.debug(wait_msg, sleep)
        if attempt < attempts - 1:
            await asyncio.sleep(sleep)
    raise LockfileError(failed_msg, paths, attempts)


class LockfileFuture:
    """Create an awaitable that uses lockfiles as a semaphore.

    Attributes:
        coro (typing.Awaitable): the coroutine to run.
        args (list): the args to pass to the coroutine.
        kwargs (dict): the kwargs to pass to the coroutine.
        retry_async_kwargs (dict): the kwargs to pass to ``retry_async``.
        use_retry_async (bool): if ``True``, use ``retry_async``.
        lockfile_kwargs (dict): the kwargs to pass to ``lockfile``.
        lockfile_map (dict): a mapping between lockfile path keys to arg/kwarg
            replacement dictionary values. e.g. ``{"path": {"find": "replace"}, ...}``

    """

    def __init__(
        self,
        coro,
        lockfile_map,
        args=None,
        kwargs=None,
        lockfile_kwargs=None,
        retry_async_kwargs=None,
        use_retry_async=False,
    ):
        """Initialize the ``LockfileFuture``.

        Args:
            coro (typing.Awaitable): the coroutine to run.
            args (list, optional): the args to pass to the coroutine. Defaults to ``[]``
            kwargs (dict, optional): the kwargs to pass to the coroutine. Defaults to ``{}``
            retry_async_kwargs (dict, optional): the kwargs to pass to ``retry_async``. Defaults to ``{}``.
            use_retry_async (bool, optional): whether to use ``retry_async``. Defaults to ``False``.
            lockfile_kwargs (dict, optional): the kwargs to pass to ``lockfile``. Defaults to ``{}``.
            lockfile_map (dict): a mapping between lockfile path keys to arg/kwarg
                replacement dictionary values. e.g. ``{"path": {"find": "replace"}, ...}``

        """
        self.coro = coro
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.lockfile_map = lockfile_map
        self.lockfile_kwargs = lockfile_kwargs or {}
        self.retry_async_kwargs = retry_async_kwargs or {}
        self.use_retry_async = use_retry_async

    def replace_args(self, obj, repl_dict):
        """Do string sprintf replacement for all strings in `obj`.

        Args:
            obj (object): an object to do string replacement in. Non-
                strings, lists, and dicts will be passed through unchanged.
            repl_dict (dict): the replacement dictionary. If a string has,
                e.g. ``%(foo)s`` in it, then a ``repl_dict`` of
                ``{"foo": "bar"}`` will replace the ``%(foo)s`` with ``bar``.

        Returns:
            obj, with string replacement if applicable.

        """
        if isinstance(obj, str):
            return obj % repl_dict
        elif isinstance(obj, (list, tuple)):
            return [self.replace_args(item, repl_dict) for item in obj]
        elif isinstance(obj, dict):
            return {key: self.replace_args(val, repl_dict) for key, val in obj.items()}
        else:
            return obj

    async def run_with_lockfile(self):
        """Run the coro with the lockfile.

        Get a lockfile, update ``self.args`` and ``self.kwargs`` with the
        corresponding ``self.lockfile_map`` value, then await ``self.coro``
        (wrapped with ``retry_async`` if ``self.use_retry_async``).

        """
        async with lockfile(
            self.lockfile_map.keys(), **self.lockfile_kwargs
        ) as lockfile_path:
            args = self.replace_args(self.args, self.lockfile_map[lockfile_path])
            kwargs = self.replace_args(self.kwargs, self.lockfile_map[lockfile_path])
            if self.use_retry_async:
                await retry_async(
                    self.coro, args=args, kwargs=kwargs, **self.retry_async_kwargs
                )
            else:
                await self.coro(*args, **kwargs)


# retry_async {{{1
def calculate_sleep_time(
    attempt, delay_factor=5.0, randomization_factor=0.5, max_delay=120
):
    """Calculate the sleep time between retries, in seconds.

    Based off of `taskcluster.utils.calculateSleepTime`, but with kwargs instead
    of constant `delay_factor`/`randomization_factor`/`max_delay`.  The taskcluster
    function generally slept for less than a second, which didn't always get
    past server issues.

    Args:
        attempt (int): the retry attempt number
        delay_factor (float, optional): a multiplier for the delay time.  Defaults to 5.
        randomization_factor (float, optional): a randomization multiplier for the
            delay time.  Defaults to .5.
        max_delay (float, optional): the max delay to sleep.  Defaults to 120 (seconds).

    Returns:
        float: the time to sleep, in seconds.

    """
    if attempt <= 0:
        return 0

    # We subtract one to get exponents: 1, 2, 3, 4, 5, ..
    delay = float(2 ** (attempt - 1)) * float(delay_factor)
    # Apply randomization factor.  Only increase the delay here.
    delay = delay * (randomization_factor * random.random() + 1)
    # Always limit with a maximum delay
    return min(delay, max_delay)


async def retry_async(
    func,
    attempts=5,
    sleeptime_callback=calculate_sleep_time,
    retry_exceptions=(Exception,),
    args=(),
    kwargs=None,
    sleeptime_kwargs=None,
):
    """Retry ``func``, where ``func`` is an awaitable.

    Args:
        func (function): an awaitable function.
        attempts (int, optional): the number of attempts to make.  Default is 5.
        sleeptime_callback (function, optional): the function to use to determine
            how long to sleep after each attempt.  Defaults to ``calculate_sleep_time``.
        retry_exceptions (list or exception, optional): the exception(s) to retry on.
            Defaults to ``Exception``.
        args (list, optional): the args to pass to ``function``.  Defaults to ()
        kwargs (dict, optional): the kwargs to pass to ``function``.  Defaults to
            {}.
        sleeptime_kwargs (dict, optional): the kwargs to pass to ``sleeptime_callback``.
            If None, use {}.  Defaults to None.

    Returns:
        object: the value from a successful ``function`` call

    Raises:
        Exception: the exception from a failed ``function`` call, either outside
            of the retry_exceptions, or one of those if we pass the max
            ``attempts``.

    """
    kwargs = kwargs or {}
    attempt = 1
    while True:
        try:
            return await func(*args, **kwargs)
        except retry_exceptions:
            attempt += 1
            if attempt > attempts:
                log.warning("retry_async: {}: too many retries!".format(func.__name__))
                raise
            sleeptime_kwargs = sleeptime_kwargs or {}
            sleep_time = sleeptime_callback(attempt, **sleeptime_kwargs)
            log.debug(
                "retry_async: {}: sleeping {} seconds before retry".format(
                    func.__name__, sleep_time
                )
            )
            await asyncio.sleep(sleep_time)


# request {{{1
async def request(
    url,
    timeout=60,
    method="get",
    good=(200,),
    retry_statuses=tuple(range(500, 512)),
    return_type="text",
    num_attempts=1,
    sterilized_url=None,
    **kwargs,
):
    """Async aiohttp request wrapper.

    Args:
        url (str): the url to request
        timeout (int, optional): timeout after this many seconds. Default is 60.
        method (str, optional): The request method to use.  Default is 'get'.
        good (list, optional): the set of good status codes.  Default is (200, )
        retry_statuses (list, optional): the set of status codes that result in a retry.
            Default is tuple(range(500, 512)).
        return_type (str, optional): The type of value to return.  Takes
            'json' or 'text'; other values will return the response object.
            Default is text.
        num_attempts (int, optional): The number of attempts to perform,
            retrying on a response status in ``retry_statuses``. Defaults to 1.
        sterilized_url (str, optional): If set, log using this url instead of
            the real url. This can help avoid logging credentials or tokens.
            If ``None``, log the real url. Defaults to ``None``.
        **kwargs: the kwargs to send to the aiohttp request function.

    Returns:
        object: the response text() if return_type is 'text'; the response
            json() if return_type is 'json'; the aiohttp request response
            object otherwise.

    Raises:
        RetryError: if the status code is in the retry list.
        TaskError: if the status code is not in the retry list or good list.

    """
    sterilized_url = sterilized_url or url
    async with aiohttp.ClientSession() as session:
        async with async_timeout.timeout(timeout):
            log.debug("{} {}".format(method.upper(), sterilized_url))

            async def request_helper():
                async with session.request(method, url, **kwargs) as resp:
                    log.debug("Status {}".format(resp.status))
                    message = "Bad status {}".format(resp.status)
                    if resp.status in retry_statuses:
                        raise RetryError(message)
                    if resp.status not in good:
                        raise TaskError(message)
                    if return_type == "text":
                        return await resp.text()
                    elif return_type == "json":
                        return await resp.json()
                    else:
                        return resp

            return await retry_async(
                request_helper,
                attempts=num_attempts,
                retry_exceptions=(asyncio.TimeoutError, RetryError),
            )


# download_file {{{1
async def _log_download_error(resp, log_url, msg):
    log.debug(
        msg, {"url": log_url, "status": resp.status, "body": (await resp.text())[:1000]}
    )
    for i, h in enumerate(resp.history):
        log.debug(
            "Redirect history %s: %s; body=%s",
            log_url,
            h.status,
            (await h.text())[:1000],
        )


async def download_file(url, abs_filename, log_url=None, chunk_size=128, timeout=300):
    """Download a file, async.

    Args:
        url (str): the url to download
        abs_filename (str): the path to download to
        log_url (str, optional): the url to log, should ``url`` contain sensitive information.
            If ``None``, use ``url``. Defaults to ``None``
        chunk_size (int, optional): the chunk size to read from the response
            at a time. Default is 128.
        timeout (int, optional): seconds to time out the request. Default is 300.

    """
    aiohttp_timeout = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=aiohttp_timeout) as session:
        log_url = log_url or url
        log.info("Downloading %s", log_url)
        parent_dir = os.path.dirname(abs_filename)
        async with session.get(url) as resp:
            if resp.status == 404:
                await _log_download_error(
                    resp, log_url, "404 downloading %(url)s: %(status)s; body=%(body)s"
                )
                raise Download404("{} status {}!".format(log_url, resp.status))
            elif resp.status != 200:
                await _log_download_error(
                    resp,
                    log_url,
                    "Failed to download %(url)s: %(status)s; body=%(body)s",
                )
                raise DownloadError(
                    "{} status {} is not 200!".format(log_url, resp.status)
                )
            makedirs(parent_dir)
            with open(abs_filename, "wb") as fd:
                while True:
                    chunk = await resp.content.read(chunk_size)
                    if not chunk:
                        break
                    fd.write(chunk)
        log.info("Done")
