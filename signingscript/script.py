#!/usr/bin/env python
"""Signing script."""
import aiohttp
import logging
import os
import ssl

from datadog import statsd

import scriptworker.client
from signingscript.task import build_filelist_dict, get_token, \
    sign, task_cert_type, task_signing_formats
from signingscript.utils import copy_to_dir, load_signing_server_config


log = logging.getLogger(__name__)

# Common prefix for all metric names produced from this scriptworker.
statsd.namespace = 'releng.scriptworker.signing'


# async_main {{{1
async def async_main(context):
    """Sign all the things.

    Args:
        context (Context): the signing context.

    """
    connector = _craft_aiohttp_connector(context)

    async with aiohttp.ClientSession(connector=connector) as session:
        context.session = session
        work_dir = context.config['work_dir']
        context.signing_servers = load_signing_server_config(context)
        cert_type = task_cert_type(context)
        all_signing_formats = task_signing_formats(context)
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


def _craft_aiohttp_connector(context):
    kwargs = {}
    if context.config.get('ssl_cert'):
        sslcontext = ssl.create_default_context(cafile=context.config['ssl_cert'])
        kwargs['ssl_context'] = sslcontext
    return aiohttp.TCPConnector(**kwargs)


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


def main():
    """Start signing script."""
    return scriptworker.client.sync_main(async_main, default_config=get_default_config())


__name__ == '__main__' and main()
