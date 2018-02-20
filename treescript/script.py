#!/usr/bin/env python
"""Tree manipulation script."""
import aiohttp
import asyncio
import logging
import os
import sys
import traceback

import scriptworker.client
from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException, ScriptWorkerException
from treescript.task import validate_task_schema
from treescript.utils import load_json, task_action_types, is_dry_run
from treescript.mercurial import log_mercurial_version, validate_robustcheckout_works, \
    checkout_repo, do_tagging, log_outgoing, push
from treescript.versionmanip import bump_version

log = logging.getLogger(__name__)


# TreeContext {{{1
class TreeContext(Context):
    """Status and configuration object."""

    def __init__(self):
        """Initialize TreeContext."""
        super(TreeContext, self).__init__()

    def write_json(self, *args):
        """Stub out the ``write_json`` method."""
        pass


# do_actions {{{1
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
async def async_main(context, conn=None):
    """Run all the vcs things.

    Args:
        context (TreeContext): the treescript context.

    """
    async with aiohttp.ClientSession(connector=conn) as session:
        context.session = session
        work_dir = context.config['work_dir']
        context.task = scriptworker.client.get_task(context.config)
        log.info("validating task")
        validate_task_schema(context)
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


# main {{{1
def usage():
    """Print usage and die."""
    print("Usage: {} CONFIG_FILE".format(sys.argv[0]), file=sys.stderr)
    sys.exit(1)


def main(config_path=None):
    """Create the context, logging, and pass off execution to ``async_main``.

    Args:
        config_path (str, optional): the path to the config file.  If `None`, use
            `sys.argv[1]`.  Defaults to None.

    """
    context = TreeContext()
    context.config = get_default_config()
    if config_path is None:
        if len(sys.argv) != 2:
            usage()
        config_path = sys.argv[1]
    context.config.update(load_json(path=config_path))
    if context.config.get('verbose'):
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=log_level
    )
    logging.getLogger("taskcluster").setLevel(logging.WARNING)
    loop = asyncio.get_event_loop()
    conn = aiohttp.TCPConnector()
    try:
        loop.run_until_complete(async_main(context, conn=conn))
    except ScriptWorkerTaskException as exc:
        traceback.print_exc()
        sys.exit(exc.exit_code)


__name__ == '__main__' and main()
