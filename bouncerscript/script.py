#!/usr/bin/env python3
""" Bouncer main script
"""
import aiohttp
import asyncio
import logging
import sys
import traceback

from scriptworker.client import get_task
from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException

from bouncerscript.utils import (
    load_json, api_add_product, api_add_location, product_exists,
)
from bouncerscript.task import (
    validate_task_schema, get_task_action, get_task_server,
)


log = logging.getLogger(__name__)


async def bouncer_submission(context):
    log.info("Preparing to submit information to bouncer")

    submissions = context.task["payload"]["submission_entries"]
    for product_name, pr_config in submissions.items():
        if await product_exists(context, product_name):
            log.warning("Product {} already exists. Skipping ...".format(product_name))
            continue

        log.info("Adding {} ...".format(product_name))
        await api_add_product(
            context,
            product_name=product_name,
            add_locales=pr_config["options"]["add_locales"],
            ssl_only=pr_config["options"]["ssl_only"]
        )

        log.info("Adding corresponding paths ...")
        for platform, path in pr_config["paths_per_bouncer_platform"].items():
            await api_add_location(context, product_name, platform, path)


async def bouncer_aliases(context):
    pass


# action_map {{{1
action_map = {
    'submission': {
        'schema': 'bouncer_submission_schema',
        'function': bouncer_submission,
    },
    'aliases': {
        'schema': 'bouncer_aliases_schema',
        'function': bouncer_aliases
    }
}


async def async_main(context):
    context.task = get_task(context.config)

    # determine the task server and action
    context.server = get_task_server(context.task, context.config)
    context.action = get_task_action(context.task, context.config)

    # perform schema validation for the corresponding type of task
    validate_task_schema(context, action_map[context.action]['schema'])

    # perform the appropriate behavior
    await action_map[context.action]['function'](context)


def usage():
    print("Usage: {} CONFIG_FILE".format(sys.argv[0]), file=sys.stderr)
    sys.exit(1)


def craft_logging_config(context):
    return {
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'level': logging.DEBUG if context.config.get('verbose') else logging.INFO
    }


def main(name=None, config_path=None, close_loop=True):
    if name not in (None, '__main__'):
        return
    context = Context()
    context.config = dict()
    if config_path is None:
        if len(sys.argv) != 2:
            usage()
        config_path = sys.argv[1]
    context.config.update(load_json(path=config_path))

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


main(name=__name__)
