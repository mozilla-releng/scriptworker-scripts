#!/usr/bin/env python
"""Tree manipulation script."""
import aiohttp
import logging
import os

import scriptworker.client
from scriptworker.exceptions import ScriptWorkerException
from treescript.utils import task_action_types, is_dry_run
from treescript.mercurial import log_mercurial_version, validate_robustcheckout_works, \
    checkout_repo, do_tagging, log_outgoing, push
from treescript.versionmanip import bump_version

log = logging.getLogger(__name__)


async def do_actions(context, actions, directory):
    """Perform the set of actions that treescript can perform.

    The actions happen in order, tagging, ver bump, then push
    """
    short_actions = [a.rsplit(':', 1)[1] for a in actions]
    short_actions.sort()  # Order we want to run in, just happens to be alphabetical sort.
    for action in short_actions:
        if 'tagging' == action:
            await do_tagging(context, directory)
        elif 'version_bump' == action:
            await bump_version(context)
        elif 'push' == action:
            pass  # handled after log_outgoing
        else:
            raise NotImplementedError("Unexpected action")
    await log_outgoing(context, directory)
    if is_dry_run(context.task):
        log.info("Not pushing changes, dry_run was forced")
    elif 'push' in short_actions:
        await push(context)
    else:
        log.info("Not pushing changes, lacking scopes")


# async_main {{{1
async def async_main(context):
    """Run all the vcs things.

    Args:
        context (TreeContext): the treescript context.

    """
    connector = aiohttp.TCPConnector()
    async with aiohttp.ClientSession(connector=connector) as session:
        context.session = session
        work_dir = context.config['work_dir']
        actions_to_perform = task_action_types(context.task)
        await log_mercurial_version(context)
        if not await validate_robustcheckout_works(context):
            raise ScriptWorkerException("Robustcheckout can't run on our version of hg, aborting")
        await checkout_repo(context, work_dir)
        if actions_to_perform:
            await do_actions(context, actions_to_perform, work_dir)
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
        'work_dir': os.path.join(base_dir, 'work_dir'),
        'hg': 'hg',
        'schema_file': os.path.join(os.path.dirname(__file__), 'data', 'treescript_task_schema.json'),
    }
    return default_config


def main():
    """Start treescript."""
    return scriptworker.client.sync_main(async_main, default_config=get_default_config())


__name__ == '__main__' and main()
