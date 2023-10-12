import logging
import os

from treescript.github import git as vcs
from treescript.github.versionmanip import bump_version
from treescript.exceptions import TreeScriptError
from treescript.util.task import get_source_repo, should_push, task_action_types

log = logging.getLogger(__name__)


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
    await vcs.checkout_repo(config, task, repo_path)

    num_changes = 0
    if "version_bump" in actions:
        num_changes += await bump_version(config, task, repo_path)

    num_outgoing = await vcs.log_outgoing(config, task, repo_path)
    if num_outgoing != num_changes:
        raise TreeScriptError("Outgoing changesets don't match number of expected changesets!" " {} vs {}".format(num_outgoing, num_changes))
    if should_push(task, actions):
        if num_changes:
            await vcs.push(config, task, repo_path, target_repo=get_source_repo(task))
        else:
            log.info("No changes; skipping push.")
    await vcs.strip_outgoing(config, task, repo_path)

