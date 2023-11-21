#!/usr/bin/env python
"""Treescript android-l10n import and sync support.
"""
import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
from compare_locales import parser, paths

from scriptworker_client.aio import retry_async

from treescript.gecko import mercurial as vcs
from treescript.util.task import CLOSED_TREE_MSG, DONTBUILD_MSG, get_dontbuild, get_ignore_closed_tree, get_android_l10n_import_info, get_android_l10n_sync_info
from treescript.util.treestatus import check_treestatus

log = logging.getLogger(__name__)


# get_android_l10n_files_toml {{{1
def get_android_l10n_files_toml(toml_path, search_path=None):
    """Extract list of localized files from project configuration (TOML)"""

    basedir = os.path.dirname(toml_path)
    project_config = paths.TOMLParser().parse(toml_path, env={"l10n_base": ""})
    basedir = os.path.join(basedir, project_config.root)

    l10n_files = []
    if search_path:
        reldir = search_path
    else:
        reldir = basedir
    for locale in project_config.all_locales:
        log.info(f"Creating list of files for locale: {locale}.")
        files = paths.ProjectFiles(locale, [project_config])

        for l10n_file, reference_file, _, _ in files:
            # Ignore missing files for locale
            if not os.path.exists(l10n_file):
                continue
            # Ignore if reference file does not exist
            if not os.path.exists(reference_file):
                continue

            l10n_files.append(
                {
                    "abs_path": l10n_file,
                    "rel_path": os.path.relpath(l10n_file, reldir),
                }
            )

    return l10n_files


# copy_android_l10n_files {{{1
def copy_android_l10n_files(l10n_files, src_repo_path, dest_repo_path):
    """Copy localized files in code repository"""

    log.info(f"Files to copy: {len(l10n_files)}.")
    for l10n_file in l10n_files:
        if src_repo_path:
            src_file = os.path.join(src_repo_path, l10n_file["rel_path"])
        else:
            src_file = l10n_file["abs_path"]
        dest_file = os.path.join(dest_repo_path, l10n_file["rel_path"])
        log.info(f"  {src_file} -> {dest_file}")
        # Make sure that the folder exists, then copy file as is
        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
        shutil.copy2(src_file, dest_file)


# build_commit_message {{{1
def build_commit_message(description, dontbuild=False, ignore_closed_tree=False):
    """Build a commit message for android-l10n import.

    Args:
        dontbuild (bool, optional): whether to add ``DONTBUILD`` to the
            comment. Defaults to ``False``
        ignore_closed_tree (bool, optional): whether to add ``CLOSED TREE``
            to the comment. Defaults to ``False``.

    Returns:
        str: the commit message

    """
    approval_str = "r=release a=android_l10n-import"
    if dontbuild:
        approval_str += DONTBUILD_MSG
    if ignore_closed_tree:
        approval_str += CLOSED_TREE_MSG
    message = f"no bug - {description} {approval_str}\n\n"
    return message


# android_l10n_action {{{1
async def android_l10n_action(config, task, task_info, repo_path, from_repo_path, description, search_path, src_path, toml_key):
    """Perform a android_l10n string import or sync action.

    Args:
        config (dict): the running config
        task (dict): the running task
        task_info (dict): the task's android_l10n_import/sync_info
        repo_path (str): the source directory
        from_repo_path (str): the source directory
        description (str): commit message description
        search_path (str): search path passed to get_android_l10n_files_toml
        src_path (str): src path passed to copy_android_l10n_files
        toml_key (str): dict key to use when building destination path

    Returns:
        int: non-zero if there are any changes.

    """
    ignore_closed_tree = get_ignore_closed_tree(task)
    if not ignore_closed_tree:
        if not await check_treestatus(config, task):
            log.info("Treestatus is closed; skipping android-l10n action.")
            return 0

    dontbuild = get_dontbuild(task)

    for toml_info in task_info["toml_info"]:
        toml_path = os.path.join(from_repo_path, toml_info["toml_path"])
        l10n_files = get_android_l10n_files_toml(toml_path, search_path)
        dest_path = os.path.join(repo_path, toml_info[toml_key])
        os.makedirs(dest_path, exist_ok=True)
        copy_android_l10n_files(l10n_files, src_path, dest_path)
        shutil.copy2(toml_path, dest_path)

    message = build_commit_message(description, dontbuild=dontbuild, ignore_closed_tree=ignore_closed_tree)
    await vcs.commit(config, repo_path, message)

    changes = 1

    return changes


# android_l10n_import {{{1
async def android_l10n_import(config, task, repo_path):
    """Perform a android_l10n string import.

    This function takes its inputs from its task.
    It reads the specified toml files to determine a list of
    locale resource files from the android_l10n repo and copies
    those from android_l10n into the source repo (typically
    autoland).

    Args:
        config (dict): the running config
        task (dict): the running task
        repo_path (str): the source directory

    Returns:
        int: non-zero if there are any changes.

    """
    log.info("Preparing to import android-l10n changes.")

    description = "Import translations from android-l10n"
    task_info = get_android_l10n_import_info(task)
    from_repo_path = tempfile.mkdtemp()
    try:
        from_repo_url = task_info["from_repo_url"]
        cmd = ["git", "clone", from_repo_url, from_repo_path]
        subprocess.run(cmd, text=True, check=True)
        search_path = None
        changes = await android_l10n_action(config, task, task_info, repo_path, from_repo_path, description, search_path, None, "dest_path")
    finally:
        shutil.rmtree(from_repo_path, ignore_errors=True)

    return changes


# android_l10n_sync {{{1
async def android_l10n_sync(config, task, repo_path):
    """Perform a android_l10n string sync.
    This function takes its inputs from its task.
    It reads the specified toml files to determine a list of
    locale resource files from the from_repo and copies
    those into the source repo (typically from mozilla-central
    into mozilla-beta).

    Args:
        config (dict): the running config
        task (dict): the running task
        repo_path (str): the source directory

    Returns:
        int: non-zero if there are any changes.

    """
    log.info("Preparing to sync android-l10n changes.")

    description = "Merge android-l10n translations from mozilla-central"
    task_info = get_android_l10n_sync_info(task)
    from_repo_path = tempfile.mkdtemp()
    try:
        from_repo_url = task_info["from_repo_url"]
        await vcs.checkout_repo(config, task, from_repo_url, from_repo_path)
        search_path = from_repo_path
        changes = await android_l10n_action(config, task, task_info, repo_path, from_repo_path, description, search_path, from_repo_path, "toml_path")
    finally:
        shutil.rmtree(from_repo_path, ignore_errors=True)

    return changes
