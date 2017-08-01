#!/usr/bin/env python
"""Signing script."""
import aiohttp
import asyncio
import logging
import os
import ssl
import sys
import traceback

import scriptworker.client
from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException
from signingscript.sign import task_cert_type
from signingscript.task import build_filelist_dict, get_token, \
    sign, task_signing_formats, validate_task_schema
from signingscript.utils import copy_to_dir, load_json, load_signing_server_config


log = logging.getLogger(__name__)


# SigningContext {{{1
class SigningContext(Context):
    """Status and configuration object."""

    signing_servers = None

    def __init__(self):
        """Initialize SigningContext."""
        super(SigningContext, self).__init__()

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
        context.signing_servers = load_signing_server_config(context)
        cert_type = task_cert_type(context.task)
        all_signing_formats = task_signing_formats(context.task)
        log.info("getting token")
        await get_token(context, os.path.join(work_dir, 'token'), cert_type, all_signing_formats)
        filelist_dict = build_filelist_dict(context, all_signing_formats)
        for path, path_dict in filelist_dict.items():
            copy_to_dir(path_dict['full_path'], context.config['work_dir'], target=path)
            log.info("signing %s", path)
            output_files = await sign(
                context, os.path.join(work_dir, path), path_dict['formats']
            )
            for source in output_files:
                source = os.path.relpath(source, work_dir)
                copy_to_dir(
                    os.path.join(work_dir, source), context.config['artifact_dir'], target=source
                )
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
        'signing_server_config': 'server_config.json',
        'work_dir': os.path.join(base_dir, 'work_dir'),
        'artifact_dir': os.path.join(base_dir, '/src/signing/artifact_dir'),
        'my_ip': "127.0.0.1",
        'token_duration_seconds': 20 * 60,
        'ssl_cert': None,
        'signtool': "signtool",
        'schema_file': os.path.join(os.path.dirname(__file__), 'data', 'signing_task_schema.json'),
        'verbose': True,
        'zipalign': 'zipalign',
        'dmg': 'dmg',
        'hfsplus': 'hfsplus',
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
    context = SigningContext()
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
    kwargs = {}
    if context.config.get('ssl_cert'):
        sslcontext = ssl.create_default_context(cafile=context.config['ssl_cert'])
        kwargs['ssl_context'] = sslcontext
    conn = aiohttp.TCPConnector(**kwargs)
    try:
        loop.run_until_complete(async_main(context, conn=conn))
    except ScriptWorkerTaskException as exc:
        traceback.print_exc()
        sys.exit(exc.exit_code)


__name__ == '__main__' and main()
