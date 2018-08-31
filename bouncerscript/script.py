#!/usr/bin/env python3
""" Bouncer main script
"""
import logging

from bouncerscript.task import (
    get_task_action, get_task_server, validate_task_schema,
    check_product_names_match_aliases, check_locations_match,
    check_path_matches_destination, check_aliases_match
)
from bouncerscript.utils import (
    api_add_location, api_add_product, api_update_alias, does_product_exist,
    does_location_path_exist, get_locations_paths
)
from scriptworker import client
from scriptworker.exceptions import (
    TaskVerificationError, ScriptWorkerTaskException
)


log = logging.getLogger(__name__)


async def bouncer_submission(context):
    """Implement the bouncer submission behavior"""
    log.info("Preparing to submit information to bouncer")
    submissions = context.task["payload"]["submission_entries"]

    for product_name, pr_config in submissions.items():
        if await does_product_exist(context, product_name):
            log.warning('Product "{}" already exists. Skipping...'.format(product_name))
        else:
            log.info('Adding product "{}"...'.format(product_name))
            await api_add_product(
                context,
                product_name=product_name,
                add_locales=pr_config["options"]["add_locales"],
                ssl_only=pr_config["options"]["ssl_only"]
            )
            log.info("Sanity check to ensure product has been successfully added...")
            if not await does_product_exist(context, product_name):
                raise ScriptWorkerTaskException("Bouncer entries are corrupt")

        log.info("Sanity check submission entries before updating ...")
        for platform, path in pr_config["paths_per_bouncer_platform"].items():
            check_path_matches_destination(product_name, path)
        log.info("All submission entries look good before updating them!")

        log.info("Adding corresponding paths ...")
        for platform, path in pr_config["paths_per_bouncer_platform"].items():
            if await does_location_path_exist(context, product_name, path):
                log.warning('Path "{}" for product "{}" already exists. Skipping...'.format(path, product_name))
            else:
                await api_add_location(context, product_name, platform, path)

        log.info("Sanity check to ensure locations have been successfully added...")
        locations_paths = await get_locations_paths(context, product_name)
        check_locations_match(locations_paths, pr_config["paths_per_bouncer_platform"])
        log.info("All entries look good, bouncer has been correctly updated!")


async def bouncer_aliases(context):
    """Implement the bouncer aliases behavior"""
    log.info("Preparing to update aliases information in bouncer")
    aliases = context.task["payload"]["aliases_entries"]

    log.info("Sanity check versions and aliases before updating ...")
    check_product_names_match_aliases(context)
    log.info("All bouncer aliases look good before updating them!")

    log.info("Updating aliases within bouncer...")
    for alias, product_name in aliases.items():
        log.info("Updating {} with {} product".format(alias, product_name))
        await api_update_alias(context, alias, product_name)

    log.info("Sanity check to ensure aliases have been successfully updated...")
    await check_aliases_match(context)
    log.info("All entries look good, bouncer has been correctly updated!")


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
