#!/usr/bin/env python
"""Utility functions."""
import asyncio
import logging
import os
import zipfile

from scriptworker_client.utils import (
    run_command,
)
from iscript.exceptions import IScriptError

log = logging.getLogger(__name__)


# _create_zipfile {{{1
async def _create_zipfile(to, files, top_dir, mode='w'):
    """Largely from signingscript.sign._create_zipfile"""
    try:
        log.info("Creating zipfile {}...".format(to))
        with zipfile.ZipFile(to, mode=mode, compression=zipfile.ZIP_DEFLATED) as z:
            for f in files:
                relpath = os.path.relpath(f, top_dir)
                z.write(f, arcname=relpath)
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

    """
    tar_exe = 'tar'
    try:
        await run_command(
            [tar_exe, 'xvf', from_], cwd=parent_dir
        )
    except Exception as e:
        raise IScriptError(e)


# _owner_filter {{{1
def _owner_filter(tarinfo_obj):
    """Force file ownership to be root, Bug 1473850."""
    tarinfo_obj.uid = 0
    tarinfo_obj.gid = 0
    tarinfo_obj.uname = ''
    tarinfo_obj.gname = ''
    return tarinfo_obj


# raise_future_exceptions {{{1
async def raise_future_exceptions(futures):
    """Await a list of futures and raise any exceptions.

    Args:
        futures (list): the futures to await

    Raises:
        Exception: on error

    Returns:
        list: the results from the futures

    """
    await asyncio.wait(futures)
    results = []
    for fut in futures:
        exc = fut.exception()
        if exc:
            raise exc
        results.append(fut.result())
    return results
