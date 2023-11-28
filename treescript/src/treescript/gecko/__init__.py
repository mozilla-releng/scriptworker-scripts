import logging
import os

from treescript.gecko import mercurial as vcs
from treescript.gecko.android_l10n import android_l10n_import, android_l10n_sync
from treescript.gecko.l10n import l10n_bump
from treescript.gecko.merges import do_merge
from treescript.gecko.nimbus import android_nimbus_update
from treescript.gecko.versionmanip import bump_version
from treescript.exceptions import TreeScriptError
from treescript.util.task import get_source_repo, should_push, task_action_types

log = logging.getLogger(__name__)


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
            log.info("pushing %s to %s", revision, target_repo)
            await vcs.push(config, task, repo_path, target_repo=target_repo, revision=revision)


async def do_actions(config, task):
    """Perform the set of actions that treescript can perform.

    The actions happen in order, tagging, ver bump, then push

    Args:
        config (dict): the running config
        task (dict): the running task
    """
    work_dir = config["work_dir"]
    repo_path = os.path.join(work_dir, "src")
    actions = task_action_types(config, task)
    await vcs.log_mercurial_version(config)
    if not await vcs.validate_robustcheckout_works(config):
        raise TreeScriptError("Robustcheckout can't run on our version of hg, aborting")

    await vcs.checkout_repo(config, task, get_source_repo(task), repo_path)

    # Split the action selection up due to complexity in do_actions
    # caused by different push behaviour, and action return values.
    if "merge_day" in actions:
        await perform_merge_actions(config, task, actions, repo_path)
        return

    num_changes = 0
    if "tag" in actions:
        num_changes += await vcs.do_tagging(config, task, repo_path)
    if "version_bump" in actions:
        num_changes += await bump_version(config, task, repo_path)
    if "l10n_bump" in actions:
        num_changes += await l10n_bump(config, task, repo_path)
    if "android_l10n_import" in actions:
        num_changes += await android_l10n_import(config, task, repo_path)
    if "android_l10n_sync" in actions:
        num_changes += await android_l10n_sync(config, task, repo_path)
    if "android_nimbus_update" in actions:
        num_changes += await android_nimbus_update(config, task, repo_path)

    num_outgoing = await vcs.log_outgoing(config, task, repo_path)
    if num_outgoing != num_changes:
        raise TreeScriptError("Outgoing changesets don't match number of expected changesets!" " {} vs {}".format(num_outgoing, num_changes))
    if should_push(task, actions):
        if num_changes:
            await vcs.push(config, task, repo_path, target_repo=get_source_repo(task))
        else:
            log.info("No changes; skipping push.")
    await vcs.strip_outgoing(config, task, repo_path)
