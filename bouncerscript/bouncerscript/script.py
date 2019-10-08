#!/usr/bin/env python3
""" Bouncer main script
"""
import logging
import os

from bouncerscript.task import (
    get_task_action, get_task_server, validate_task_schema,
    check_product_names_match_aliases, check_locations_match,
    check_path_matches_destination, check_aliases_match,
    check_product_names_match_nightly_locations,
    check_location_path_matches_destination,
    check_versions_are_successive, check_version_matches_nightly_regex
)
from bouncerscript.utils import (
    api_add_location, api_add_product, api_update_alias, does_product_exist,
    get_locations_info, get_nightly_version, get_version_bumped_path,
    api_modify_location, does_location_path_exist,
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
            if await does_location_path_exist(context, product_name, platform, path):
                log.warning('Path "{}" for product "{}" already exists. Skipping...'.format(path, product_name))
            else:
                await api_add_location(context, product_name, platform, path)

        log.info("Sanity check to ensure locations have been successfully added...")
        locations_info = await get_locations_info(context, product_name)
        locations_paths = [i['path'] for i in locations_info]
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


async def bouncer_locations(context):
    """Implement the bouncer locations behaviour"""
    log.info("Preparing to update locations information in bouncer")
    bouncer_products = context.task["payload"]["bouncer_products"]

    log.info("Sanity check bouncer products before updating ...")
    check_product_names_match_nightly_locations(context)
    log.info("All bouncer products look good before updating them!")

    log.info("Sanity checking the version math makes sense ...")
    product = context.task["payload"]["product"]
    check_version_matches_nightly_regex(context.task["payload"]["version"], product)
    log.info("In-tree version from payload looks good!")

    did_bump = False
    payload_version = context.task["payload"]["version"]

    for product_name in bouncer_products:
        log.info("Sanity check to ensure product exists...")
        if not await does_product_exist(context, product_name):
            err_msg = "Cannot find product {} in bouncer".format(product_name)
            raise ScriptWorkerTaskException(err_msg)

        locations_info = await get_locations_info(context, product_name)
        for entry in locations_info:
            platform, path = entry['os'], entry['path']
            log.info("Sanity check product {} platform {}, path {} before bumping"
                     " its version ...".format(product_name, platform, path))

            check_location_path_matches_destination(product_name, path)
            current_version = get_nightly_version(product_name, path)
            if current_version == payload_version:
                log.info("No-op. Nightly version is the same")
                continue

            check_versions_are_successive(current_version, payload_version, product)
            bumped_path = get_version_bumped_path(path, current_version, payload_version)
            log.info("Modifying corresponding path with bumped one {}".format(bumped_path))
            await api_modify_location(context, product_name, platform, bumped_path)
            did_bump = True

    if did_bump:
        log.info("Sanity check to ensure all bouncer products have been successfully bumped...")
        for product_name in bouncer_products:
            locations_info = await get_locations_info(context, product_name)
            for entry in locations_info:
                platform, path = entry['os'], entry['path']
                log.info("Sanity check product {} platform {}, path {} after bumping its "
                         "version ...".format(product_name, platform, path))
                check_location_path_matches_destination(product_name, path)

                log.info("Sanity checking to make sure the bump was successful...")
                if payload_version not in path:
                    err_msg = ("Couldn't find in-tree version {} in the updated "
                               "bouncer path {}".format(payload_version, path))
                    raise ScriptWorkerTaskException(err_msg)
        log.info("All bumped bouncer products look good!")


action_map = {
    'submission': bouncer_submission,
    'aliases': bouncer_aliases,
    'locations': bouncer_locations,
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
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    default_config = {
        'schema_files': {
            'submission': os.path.join(data_dir, 'bouncer_submission_task_schema.json'),
            'aliases': os.path.join(data_dir, 'bouncer_aliases_task_schema.json'),
            'locations': os.path.join(data_dir, 'bouncer_locations_task_schema.json'),
        }
    }

    client.sync_main(async_main, config_path=config_path, default_config=default_config, should_validate_task=False)


__name__ == '__main__' and main()
