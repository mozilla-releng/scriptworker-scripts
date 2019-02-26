#!/usr/bin/env python
"""Utility functions."""
import logging
import os
import tarfile
import zipfile

# TODO stop importing non-client scriptworker
from scriptworker_client.utils import (
    makedirs,
    rm,
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


# _get_tarfile_compression {{{1
def _get_tarfile_compression(compression):
    compression = compression.lstrip('.')
    if compression not in ('bz2', 'gz'):
        raise IScriptError(
            "{} not a supported tarfile compression format!".format(compression)
        )
    return compression


# _extract_tarfile {{{1
async def _extract_tarfile(from_, compression, top_dir):
    compression = _get_tarfile_compression(compression)
    try:
        files = []
        rm(top_dir)
        makedirs(top_dir)
        with tarfile.open(from_, mode='r:{}'.format(compression)) as t:
            t.extractall(path=top_dir)
            for name in t.getnames():
                path = os.path.join(top_dir, name)
                os.path.isfile(path) and files.append(path)
        return files
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


# _create_tarfile {{{1
async def _create_tarfile(to, files, compression, top_dir):
    compression = _get_tarfile_compression(compression)
    try:
        log.info("Creating tarfile {}...".format(to))
        with tarfile.open(to, mode='w:{}'.format(compression)) as t:
            for f in files:
                relpath = os.path.relpath(f, top_dir)
                t.add(f, arcname=relpath, filter=_owner_filter)
        return to
    except Exception as e:
        raise IScriptError(e)
