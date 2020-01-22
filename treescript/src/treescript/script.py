#!/usr/bin/env python
"""Tree manipulation script."""
import logging
import os

from scriptworker_client.aio import retry_async
from scriptworker_client.client import sync_main
from treescript.exceptions import CheckoutError, PushError, TreeScriptError
from treescript.l10n import l10n_bump
from treescript.mercurial import checkout_repo, do_tagging, log_mercurial_version, log_outgoing, push, strip_outgoing, validate_robustcheckout_works
from treescript.merges import do_merge
from treescript.task import get_source_repo, should_push, task_action_types
from treescript.versionmanip import bump_version

log = logging.getLogger(__name__)

MERGE_ACTION_WORD = "merge_day"


async def perform_merge_actions(config, task, actions, repo_path):
    """Perform merge day related actions.

    This has different behaviour to other treescript actions:
    * Reporting on outgoing changesets has less meaning
    * Logging outgoing changesets can easily break with the volume and content of the diffs
    * We need to do more than just |hg push -r .| since we have two branches to update

    Args:
        config (dict): the running config
        task (dict): the running task
        actions (list): the actions to perform
        repo_path (str): the source directory to use.
    """
    log.info("Starting merge day operations")
    push_activity = await do_merge(config, task, repo_path)

    if should_push(task, actions) and push_activity:
        log.info("%d branches to push", len(push_activity))
        for target_repo, revision in push_activity:
            print("pushing to", target_repo, revision)
            await push(config, task, repo_path, target_repo=target_repo, revision=revision)


async def do_actions(config, task, actions, repo_path):
    """Perform the set of actions that treescript can perform.

    The actions happen in order, tagging, ver bump, then push

    Args:
        config (dict): the running config
        task (dict): the running task
        actions (list): the actions to perform
        repo_path (str): the source directory to use.
    """
    await checkout_repo(config, task, repo_path)

    # Split the action selection up due to complexity in do_actions
    # caused by different push behaviour, and action return values.
    if MERGE_ACTION_WORD in actions:
        await perform_merge_actions(config, task, actions, repo_path)
        return

    num_changes = 0
    if "tag" in actions:
        num_changes += await do_tagging(config, task, repo_path)
    if "version_bump" in actions:
        num_changes += await bump_version(config, task, repo_path)
    if "l10n_bump" in actions:
        num_changes += await l10n_bump(config, task, repo_path)

    num_outgoing = await log_outgoing(config, task, repo_path)
    if num_outgoing != num_changes:
        raise TreeScriptError("Outgoing changesets don't match number of expected changesets!" " {} vs {}".format(num_outgoing, num_changes))
    if should_push(task, actions):
        if num_changes:
            await push(config, task, repo_path, target_repo=get_source_repo(task))
        else:
            log.info("No changes; skipping push.")
    await strip_outgoing(config, task, repo_path)


# async_main {{{1
async def async_main(config, task):
    """Run all the vcs things.

    Args:
        config (dict): the running config.
        task (dict): the running task.

    """
    work_dir = config["work_dir"]
    repo_path = os.path.join(work_dir, "src")
    actions_to_perform = task_action_types(config, task)
    await log_mercurial_version(config)
    if not await validate_robustcheckout_works(config):
        raise TreeScriptError("Robustcheckout can't run on our version of hg, aborting")
    await retry_async(do_actions, args=(config, task, actions_to_perform, repo_path), retry_exceptions=(CheckoutError, PushError))
    log.info("Done!")


# config {{{1
def get_default_config(base_dir=None):
    """Create the default config to work from.

    Args:
        base_dir (str, optional): the directory above the `work_dir` and `artifact_dir`.
            If None, use `..`  Defaults to None.

    Returns:
        dict: the default configuration dict.

    """
    base_dir = base_dir or os.path.dirname(os.getcwd())
    default_config = {
        "work_dir": os.path.join(base_dir, "work_dir"),
        "hg": "hg",
        "schema_file": os.path.join(os.path.dirname(__file__), "data", "treescript_task_schema.json"),
    }
    return default_config


def main():
    """Start treescript."""
    return sync_main(async_main, default_config=get_default_config())


__name__ == "__main__" and main()
