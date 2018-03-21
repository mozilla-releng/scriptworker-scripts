#!/usr/bin/env python3
""" Bouncer main script
"""
import logging

from bouncerscript.task import (
    get_task_action, get_task_server, validate_task_schema, check_product_names_match_aliases
)
from bouncerscript.utils import (
    api_add_location, api_add_product, api_update_alias, does_product_exists,
)
from scriptworker import client
from scriptworker.exceptions import TaskVerificationError


log = logging.getLogger(__name__)


async def bouncer_submission(context):
    """Implement the bouncer submission behavior"""
    log.info("Preparing to submit information to bouncer")

    submissions = context.task["payload"]["submission_entries"]
    for product_name, pr_config in submissions.items():
        if await does_product_exists(context, product_name):
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
    """Implement the bouncer aliases behavior"""
    aliases = context.task["payload"]["aliases_entries"]

    log.info("Sanity check versions and aliases before updating ...")
    check_product_names_match_aliases(context)

    log.info("Preparing to update aliases within bouncer")
    for alias, product_name in aliases.items():
        log.info("Updating {} with {} product".format(alias, product_name))
        await api_update_alias(context, alias, product_name)


action_map = {
    'submission': bouncer_submission,
    'aliases': bouncer_aliases,
}


async def async_main(context):
    # perform schema validation for the corresponding type of task
    validate_task_schema(context)

    # determine the task server and action
    context.server = get_task_server(context.task, context.config)
    context.action = get_task_action(context.task, context.config)

    # perform the appropriate behavior
    if action_map.get(context.action):
        await action_map[context.action](context)
    else:
        raise TaskVerificationError("Unknown action: {}!".format(context.action))


def main(config_path=None):
    client.sync_main(async_main, config_path=config_path, should_validate_task=False)


__name__ == '__main__' and main()
