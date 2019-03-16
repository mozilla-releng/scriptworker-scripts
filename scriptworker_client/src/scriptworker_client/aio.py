#!/usr/bin/env python
"""Async helper functions."""
import aiohttp
import asyncio
import async_timeout
import logging
import random

from scriptworker_client.exceptions import RetryError, TaskError, TimeoutError

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
async def semaphore_wrapper(semaphore, coro):
    """Wrap an async function with semaphores.

    Usage::

        semaphore = asyncio.Semaphore(10)  # max 10 concurrent
        futures = []
        futures.append(asyncio.ensure_future(
            semaphore, do_something(arg1, arg2, kwarg1='foo')
        ))
        await raise_future_exceptions(futures)

    Args:
        semaphore (asyncio.Semaphore): the semaphore to wrap the action with
        coro (coroutine): an asyncio coroutine

    Returns:
        the result of ``action``.

    """
    async with semaphore:
        return await coro


# retry_async {{{1
def calculate_sleep_time(attempt, delay_factor=5.0, randomization_factor=.5, max_delay=120):
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


async def retry_async(func, attempts=5, sleeptime_callback=calculate_sleep_time,
                      retry_exceptions=Exception, args=(), kwargs=None,
                      sleeptime_kwargs=None):
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
            log.debug("retry_async: {}: sleeping {} seconds before retry".format(func.__name__, sleep_time))
            await asyncio.sleep(sleep_time)


# request {{{1
async def request(url, timeout=60, method='get', good=(200, ),
                  retry_statuses=tuple(range(500, 512)), return_type='text',
                  num_attempts=1, sterilized_url=None, **kwargs):
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
                    if return_type == 'text':
                        return await resp.text()
                    elif return_type == 'json':
                        return await resp.json()
                    else:
                        return resp

            return await retry_async(
                request_helper, attempts=num_attempts,
                retry_exceptions=(asyncio.TimeoutError, RetryError),
            )
