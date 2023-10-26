import logging

from scriptworker_client.github import extract_github_repo_owner_and_name

from treescript.github.client import GithubClient
from treescript.github.versionmanip import bump_version
from treescript.util.task import get_source_repo, task_action_types

log = logging.getLogger(__name__)


async def do_actions(config, task):
    """Perform the set of actions that treescript can perform.

    The actions happen in order, tagging, ver bump, then push

    Args:
        config (dict): the running config
        task (dict): the running task
    """
    source_repo = get_source_repo(task)
    owner, repo = extract_github_repo_owner_and_name(source_repo)
    actions = task_action_types(config, task)

    async with GithubClient(config, owner, repo) as client:
        if "version_bump" in actions:
            await bump_version(client, task)
