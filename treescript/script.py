#!/usr/bin/env python
"""Signing script."""
import aiohttp
import asyncio
import logging
import os
# import ssl
import sys
import traceback

# from datadog import statsd

import scriptworker.client
from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException, ScriptWorkerException
# from signingscript.sign import task_cert_type
# from signingscript.task import build_filelist_dict, get_token, \
#     sign, task_signing_formats, validate_task_schema
from treescript.task import validate_task_schema
# from signingscript.utils import copy_to_dir, load_json, load_signing_server_config
from treescript.utils import load_json, task_action_types
from treescript.mercurial import log_mercurial_version, validate_robustcheckout_works, \
    checkout_repo

log = logging.getLogger(__name__)

# # Common prefix for all metric names produced from this scriptworker.
# statsd.namespace = 'releng.scriptworker.signing'


# SigningContext {{{1
class TreeContext(Context):
    """Status and configuration object."""

    def __init__(self):
        """Initialize SigningContext."""
        super(TreeContext, self).__init__()

    def write_json(self, *args):
        """Stub out the `write_json` method."""
        pass


# async_main {{{1
async def async_main(context, conn=None):
    """Sign all the things.

    Args:
        context (SigningContext): the signing context.

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
        # flake8
        assert work_dir
        assert actions_to_perform is not "invalid"
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
        # 'signing_server_config': 'server_config.json',
        'work_dir': os.path.join(base_dir, 'work_dir'),
        'hg': 'hg',
        # 'artifact_dir': os.path.join(base_dir, '/src/signing/artifact_dir'),
        # 'my_ip': "127.0.0.1",
        # 'token_duration_seconds': 20 * 60,
        # 'ssl_cert': None,
        # 'signtool': "signtool",
        'schema_file': os.path.join(os.path.dirname(__file__), 'data', 'treescript_task_schema.json'),
        # 'verbose': True,
        # 'zipalign': 'zipalign',
        # 'dmg': 'dmg',
        # 'hfsplus': 'hfsplus',
    }
    return default_config


# main {{{1
def usage():
    """Print usage and die."""
    print("Usage: {} CONFIG_FILE".format(sys.argv[0]), file=sys.stderr)
    sys.exit(1)


def main(config_path=None):
    """Create the context, logging, and pass off execution to `async_main`.

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
