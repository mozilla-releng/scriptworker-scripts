#!/usr/bin/env python
"""Utility functions."""
import asyncio
import logging

from scriptworker_client.utils import (
    run_command,
)
from iscript.exceptions import IScriptError, TimeoutError

log = logging.getLogger(__name__)


# create_zipfile {{{1
async def create_zipfile(to, files, top_dir):
    """Create a zipfile.

    Args:
        to (str): the path of the zipfile
        files (list): the paths to recursively add to the zip.
        top_dir (str): the top level directory. paths will be added relative
            to this directory.

    Raises:
        IScriptError: on failure

    """
    try:
        log.info("Creating zipfile {}...".format(to))
        await run_command(
            ["zip", to, *files], cwd=top_dir, exception=IScriptError
        )
        return to
    except Exception as e:
        raise IScriptError(e)


# extract_tarfile {{{1
async def extract_tarfile(from_, parent_dir):
    """Extract a tarfile.

    Args:
        from_ (str): the path to the tarball
        parent_dir (str): the path to the parent directory to extract into.
            This function currently assumes this directory has been created
            and cleaned as appropriate.

    Raises:
        IScriptError: on failure

    """
    tar_exe = 'tar'
    await run_command(
        [tar_exe, 'xvf', from_], cwd=parent_dir, exception=IScriptError
    )


# raise_future_exceptions {{{1
async def raise_future_exceptions(futures, timeout=None):
    """Await a list of futures and raise any exceptions.

    Args:
        futures (list): the futures to await
        timeout (int, optional): If not ``None``, timeout after this many seconds.
            Defaults to ``None``.

    Raises:
        Exception: on error

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
