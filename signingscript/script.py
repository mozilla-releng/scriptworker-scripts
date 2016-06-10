#!/usr/bin/env python
"""Signing script
"""
import aiohttp
import asyncio
import logging
import os
import ssl
import sys
import traceback
from urllib.parse import urlparse

import scriptworker.client
from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException
from signingscript.task import validate_task_schema
from signingscript.worker import get_token, read_temp_creds, sign

log = logging.getLogger(__name__)


class SigningContext(Context):
    signing_servers = None

    def __init__(self):
        super(SigningContext, self).__init__()

    def write_json(self, *args):
        pass


async def async_main(context):
    loop = asyncio.get_event_loop()
    work_dir = context.config['work_dir']
    context.task = scriptworker.client.get_task(context.config)
    loop.create_task(read_temp_creds(context))
    validate_task_schema(context)
    # _ scriptworker needs to validate CoT artifact
    # await sign(context)
    # X download artifacts
    # _ _ any checks here?
    # X get token
    await get_token(context, os.path.join(work_dir, 'token'), 'nightly', 'gpg')
    # X sign bits
    # X copy bits to artifact dir
    # X periodically update temp creds from disk


# main {{{1
def main(name=None):
    if name in (None, '__main__'):
        # TODO config
        context = SigningContext()
        if os.environ.get('DOCKER_HOST'):
            # The .1 on the same subnet as the DOCKER_HOST ip
            parsed = urlparse(os.environ['DOCKER_HOST'])
            parts = parsed.hostname.split('.')
            parts[3] = "1"
            my_ip = '.'.join(parts)
        else:
            my_ip = "127.0.0.1"
        context.config = {
            # TODO genericize
            'signing_server_config': 'signing_server_config.json',
            'tools_dir': '/src/signing/tools',
            'work_dir': '/src/signing/work_dir',
            'artifact_dir': '/src/signing/artifact_dir',
            'temp_creds_refresh_seconds': 330,
            'my_ip': my_ip,
            'schema_file': os.path.join(os.getcwd(), 'signingscript', 'data', 'signing_task_schema.json'),
            'verbose': True,
        }
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
        # XXX can we get the signing servers' CA cert on the scriptworkers?
        if context.config.get('ssl_cert'):
            sslcontext = ssl.create_default_context(cafile='/path/to/ca-bundle.crt')
            kwargs['ssl_context'] = sslcontext
        else:
            kwargs['verify_ssl'] = False
        conn = aiohttp.TCPConnector(**kwargs)
        with aiohttp.ClientSession(connector=conn) as session:
            context.session = session
            try:
                loop.run_until_complete(async_main(context))
            except ScriptWorkerTaskException as exc:
                traceback.print_exc()
                sys.exit(exc.exit_code)


main(name=__name__)
