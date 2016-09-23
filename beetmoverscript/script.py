#!/usr/bin/env python
"""Beetmover script
"""
import logging
import sys
import traceback

import aiohttp
import asyncio
from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException
from beetmoverscript.utils import load_json

log = logging.getLogger(__name__)


# async_main {{{1
async def async_main(context):
    log.info("Hello Scriptworker!")
    # 1. parse the task
    # 2. for each artifact in taskid
    #   a. download
    #   b. scan
    #   c. upload


# main {{{1
def usage():
    print("Usage: {} CONFIG_FILE".format(sys.argv[0]), file=sys.stderr)
    sys.exit(1)


def main(name=None, config_path=None):
    if name not in (None, '__main__'):
        return
    if config_path is None:
        if len(sys.argv) != 2:
            usage()
        config_path = sys.argv[1]
    context = Context()
    context.config.update(load_json(path=config_path))

    log_level = logging.DEBUG
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=log_level
    )
    logging.getLogger("taskcluster").setLevel(logging.WARNING)
    loop = asyncio.get_event_loop()
    conn = aiohttp.TCPConnector()
    with aiohttp.ClientSession(connector=conn) as session:
        context.session = session
        try:
            loop.run_until_complete(async_main(context))
        except ScriptWorkerTaskException as exc:
            traceback.print_exc()
            sys.exit(exc.exit_code)
    loop.close()

    async_main(config_path)

main(name=__name__)
