#!/usr/bin/env python
"""Treescript l10n support."""
import logging
import os

from treescript.exceptions import TaskVerificationError, TreeScriptError
from treescript.mercurial import run_hg_command
from treescript.task import DONTBUILD_MSG, get_version_bump_info, get_dontbuild

log = logging.getLogger(__name__)


async def l10n_bump(config, task, source_repo):
    """Perform a version bump.

    This function takes its inputs from task by using the ``get_version_bump_info``
    function from treescript.task. Using `next_version` and `files`.

    This function does nothing (but logs) if the current version and next version
    match, and nothing if the next_version is actually less than current_version.

    Args:
        config (dict): the running config
        task (dict): the running task
        source_repo (str): the source directory

    raises:
        TaskverificationError: if a file specified is not allowed, or
                               if the file is not in the target repository.

    """
    ...
