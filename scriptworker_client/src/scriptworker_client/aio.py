#!/usr/bin/env python
"""Async helper functions."""
import asyncio
import logging
import random

from scriptworker_client.exceptions import TimeoutError

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
    done, pending = await asyncio.wait(futures, timeout=timeout)
    if pending:
        raise TimeoutError("{} futures still pending after timeout of {}".format(
            len(pending), timeout
        ))
    results = []
    for fut in futures:
        exc = fut.exception()
        if exc:
            raise exc
        results.append(fut.result())
    return results


# semaphore_wrapper {{{1
async def semaphore_wrapper(semaphore, action, *args, **kwargs):
    """Wrap an async function with semaphores.

    Usage::

        semaphore = asyncio.Semaphore(10)  # max 10 concurrent
        futures = []
        futures.append(asyncio.ensure_future(
            semaphore, do_something, arg1, arg2, kwarg1='foo'
        ))
        await raise_future_exceptions(futures)

    Args:
        semaphore (asyncio.Semaphore): the semaphore to wrap the action with
        action (callable): an asyncio coroutine
        *args: the args to send to the coroutine
        **kwargs: the kwargs to send to the coroutine

    Returns:
        the result of ``action``.

    """
    async with semaphore:
        return await action(*args, **kwargs)


# retry_async {{{1
def calculate_sleep_time(attempt):
    """Calculate retry sleep time.

    From ``taskcluster.utils`` and the go client
    https://github.com/taskcluster/go-got/blob/031f55c/backoff.go#L24-L29

    Args:
        attempt (int): the attempt number

    Returns:
        float: the sleep time between attempts

    """
    DELAY_FACTOR = 0.1
    RANDOMIZATION_FACTOR = 0.25
    MAX_DELAY = 30

    if attempt <= 0:
        return 0

    # We subtract one to get exponents: 1, 2, 3, 4, 5, ..
    delay = float(2 ** (attempt - 1)) * float(DELAY_FACTOR)
    # Apply randomization factor
    delay = delay * (RANDOMIZATION_FACTOR * (random.random() * 2 - 1) + 1)
    # Always limit with a maximum delay
    return min(delay, MAX_DELAY)


async def retry_async(func, attempts=5, sleeptime_callback=calculate_sleep_time,
                      retry_exceptions=Exception, args=(), kwargs=None,
                      sleeptime_kwargs=None):
    """Retry ``func``, where ``func`` is an awaitable.

    Args:
        func (function): an awaitable function.
        attempts (int, optional): the number of attempts to make.  Default is 5.
        sleeptime_callback (function, optional): the function to use to determine
            how long to sleep after each attempt.  Defaults to ``calculateSleepTime``.
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
            log.debug("retry_async: {}: sleeping {} seconds before retry".format(func.__name__, sleep_time))
            await asyncio.sleep(sleep_time)
