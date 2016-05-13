#!/usr/bin/env python
"""Signing script
"""
import aiohttp
import asyncio
import logging
import os
import sys
import traceback

import scriptworker.client
from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException

log = logging.getLogger(__name__)


class SigningContext(Context):
    signing_servers = None

    def __init__(self):
        super(SigningContext, self).__init__()

    def write_json(self, *args):
        pass


async def async_main(context):
    context.task = scriptworker.client.get_task(context.config)
    # validate:
    # - scriptworker.client.validate_task_schema(context.task, schema)
    # - listTaskGroup(taskGroupId, {continuationToken, limit}) : result
    # - -(does this need to be done in the scriptworker?)
    # - - find decision task
    # - - query artifacts
    # - - download graph
    # - - verify artifact graph against taskgroup
    # - if/when audit service is available, query it
    # download artifacts
    # - any checks here?
    # get token
    # sign bits
    # copy bits to artifact dir


# main {{{1
def main(name=None):
    if name in (None, '__main__'):
        # TODO config
        context = SigningContext()
        context.config = {
            'work_dir': '/src/signing/work_dir',
            'artifact_dir': '/src/signing/artifact_dir',
            'schema_file': os.path.join(os.getcwd(), "data", "signing_task_schema.json"),
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
        with aiohttp.ClientSession() as session:
            context.session = session
            try:
                loop.run_until_complete(async_main(context))
            except ScriptWorkerTaskException as exc:
                traceback.print_exc()
                sys.exit(exc.exit_code)


main(name=__name__)
