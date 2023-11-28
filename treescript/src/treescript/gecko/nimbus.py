#!/usr/bin/env python
"""Treescript Nimbus support.
"""
import logging
import os
import subprocess

from scriptworker_client.aio import request
from treescript.exceptions import CheckoutError
from treescript.gecko import mercurial as vcs
from treescript.util.task import CLOSED_TREE_MSG, DONTBUILD_MSG, get_dontbuild, get_ignore_closed_tree, get_android_nimbus_update_info, get_short_source_repo
from treescript.util.treestatus import check_treestatus

log = logging.getLogger(__name__)


# build_commit_message {{{1
def build_commit_message(description, dontbuild=False, ignore_closed_tree=False):
    """Build a commit message for nimbus update.

    Args:
        dontbuild (bool, optional): whether to add ``DONTBUILD`` to the
            comment. Defaults to ``False``
        ignore_closed_tree (bool, optional): whether to add ``CLOSED TREE``
            to the comment. Defaults to ``False``.

    Returns:
        str: the commit message

    """
    approval_str = "r=release a=nimbus"
    if dontbuild:
        approval_str += DONTBUILD_MSG
    if ignore_closed_tree:
        approval_str += CLOSED_TREE_MSG
    message = f"no bug - {description} {approval_str}\n\n"
    return message


# android_nimbus_update {{{1
async def android_nimbus_update(config, task, repo_path):
    """Update a Nimbus experiments.json file.
    This function takes its inputs from its task.
    It reads the specified url to get the desired contents of
    an android project's experiments.json file and updates
    that file if it has changed.

    Args:
        config (dict): the running config
        task (dict): the running task
        repo_path (str): the source directory

    Returns:
        int: non-zero if there are any changes.

    """
    log.info("Preparing to sync android-nimbus changes.")

    task_info = get_android_nimbus_update_info(task)

    ignore_closed_tree = get_ignore_closed_tree(task)
    if not ignore_closed_tree:
        if not await check_treestatus(config, task):
            tree = get_short_source_repo(task)
            log.info(f"Treestatus reports {tree} is closed; skipping android-nimbus action.")
            return 0

    dontbuild = get_dontbuild(task)

    changes = 0
    for update in task_info["updates"]:
        app_name = update["app_name"]
        experiments_path = update["experiments_path"]
        url = update["experiments_url"]

        description = f"Update {app_name} initial experiments JSON for Nimbus"
        log.info(description)

        response = await request(url, num_attempts=3)

        # Customize the json file by extracting the part matching the app name
        # (ie, Focus and Fenix usually use the same experiments_url, but require
        # different json content).
        cmd = ["jq", f'{{"data":map(select(.appName == "{app_name}"))}}']
        p = subprocess.run(cmd, stdout=subprocess.PIPE, input=response, text=True)
        new_contents = p.stdout

        old_contents = ""
        experiments_path = os.path.join(repo_path, experiments_path)
        if os.path.exists(experiments_path):
            with open(experiments_path, "r") as f:
                old_contents = f.read()
        else:
            log.info(f"Experiments-path {experiments_path} not found.")
            continue

        if old_contents == new_contents:
            log.info("No changes found.")
        else:
            with open(experiments_path, "w") as f:
                f.write(new_contents)
            message = build_commit_message(description, dontbuild=dontbuild, ignore_closed_tree=ignore_closed_tree)
            await vcs.commit(config, repo_path, message)
            changes += 1

    return changes
