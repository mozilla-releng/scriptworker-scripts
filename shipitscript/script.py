#!/usr/bin/env python3
""" ShipIt main script
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
from scriptworker.utils import load_json_or_yaml

from shipitscript.ship_actions import mark_as_shipped
from shipitscript.task import validate_task_schema, get_ship_it_instance_config_from_scope


log = logging.getLogger(__name__)


async def async_main(context):
    context.task = scriptworker.client.get_task(context.config)
    log.info('Validating task definition...')
    validate_task_schema(context)
    ship_it_instance_config = get_ship_it_instance_config_from_scope(context)

    release_name = context.task['payload']['release_name']
    mark_as_shipped(ship_it_instance_config, release_name)
    log.info('Done!')


def get_default_config():
    cwd = os.getcwd()
    parent_dir = os.path.dirname(cwd)

    return {
        'work_dir': os.path.join(parent_dir, 'work_dir'),
        'schema_file': os.path.join(cwd, 'shipitscript', 'data', 'shipit_task_schema.json'),
        'verbose': False,
    }


def usage():
    print("Usage: {} CONFIG_FILE".format(sys.argv[0]), file=sys.stderr)
    sys.exit(1)


def main(name=None, config_path=None, close_loop=True):
    if name not in (None, '__main__'):
        return
    context = Context()
    context.config = get_default_config()
    if config_path is None:
        if len(sys.argv) != 2:
            usage()
        config_path = sys.argv[1]
    with open(config_path) as f:
        print(f.read())

    context.config.update(load_json_or_yaml(config_path, is_path=True))

    logging.basicConfig(**craft_logging_config(context))
    logging.getLogger('taskcluster').setLevel(logging.WARNING)

    loop = asyncio.get_event_loop()
    with aiohttp.ClientSession() as session:
        context.session = session
        try:
            loop.run_until_complete(async_main(context))
        except ScriptWorkerTaskException as exc:
            traceback.print_exc()
            sys.exit(exc.exit_code)

    if close_loop:
        # Loop cannot be reopen once closed. Not closing it allows to run several tests on main()
        loop.close()


def craft_logging_config(context):
    return {
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'level': logging.DEBUG if context.config.get('verbose') else logging.INFO
    }


main(name=__name__)
