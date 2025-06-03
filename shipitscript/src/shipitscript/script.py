#!/usr/bin/env python3
"""ShipIt main script"""

import logging
import os
import sys

import mozilla_repo_urls
from scriptworker import client
from scriptworker.exceptions import TaskVerificationError

from shipitscript import ship_actions
from shipitscript.task import get_ship_it_instance_config_from_scope, get_task_action, validate_task_schema

log = logging.getLogger(__name__)


async def async_main(context):
    validate_task_schema(context)

    context.ship_it_instance_config = get_ship_it_instance_config_from_scope(context)
    context.action = get_task_action(context)

    # action has already been validated
    ACTION_MAP[context.action](context)
    log.info("Success!")


def mark_as_shipped_action(context):
    """Action to perform is to tell Ship-it API that a release can be marked
    as shipped"""
    release_name = context.task["payload"]["release_name"]

    log.info("Marking the release as shipped ...")
    ship_actions.mark_as_shipped_v2(context.ship_it_instance_config, release_name)


def create_new_release_action(context):
    """Determine if there is a shippable release and create it if so in Shipit"""
    payload = context.task["payload"]
    shipit_config = context.ship_it_instance_config
    product = payload["product"]
    branch = payload["branch"]
    phase = payload["phase"]
    version = payload["version"]
    cron_revision = payload["cron_revision"]  # rev that cron triggered on

    source_url = None
    repository_url = None

    if "source" in context.task.get("metadata", {}):
        source_url = mozilla_repo_urls.parse(context.task["metadata"]["source"])

    log.info("Determining most recent shipped revision based off we released")
    last_shipped_revision = ship_actions.get_most_recent_shipped_revision(shipit_config, product, branch)

    if source_url is None or source_url.platform == "hgmo":
        if not last_shipped_revision:
            log.error("Something is broken under the sun if no shipped revision")
            sys.exit(1)
        log.info(f"Last shipped revision is {last_shipped_revision}")

        log.info("Determining most recent shippable revision")

        if source_url is not None:
            repository_url = f"https://hg.mozilla.org/{source_url.repo}"

        shippable_revision = ship_actions.get_shippable_revision(branch, last_shipped_revision, cron_revision, source_url)
    elif source_url.platform == "github":
        repository_url = f"https://github.com/{source_url.owner}/{source_url.repo}"

        if last_shipped_revision:
            log.info(f"Last shipped revision is {last_shipped_revision}")

            log.info("Determining if cron revision is shippable")

            shippable_revision = ship_actions.get_shippable_revision(branch, last_shipped_revision, cron_revision, source_url)
        else:
            shippable_revision = cron_revision
            log.info("This is the first release on this branch, shipping `cron_revision` {shippable_revision}")
    else:
        raise TaskVerificationError(f"Unknown repository type for URL: {source_url}.")

    if not shippable_revision:
        log.info("No valid shippable revision found, silent exit ...")
        return

    log.info(f"The shippable revision found is {shippable_revision}")

    log.info("Starting a new release in Ship-it ...")
    ship_actions.start_new_release(shipit_config, product, branch, version, shippable_revision, phase, repository_url)


def update_product_channel_version_action(context):
    """Update product channel version in shipit (if needed.)"""
    payload = context.task["payload"]
    shipit_config = context.ship_it_instance_config
    product = payload["product"]
    channel = payload["channel"]
    version = payload["version"]
    log.info(f"Determining the current {product} {channel} version")
    current_product_channel_version = ship_actions.get_product_channel_version(shipit_config, product, channel)
    if current_product_channel_version == version:
        log.info(f"The {product} {channel} version is already {version}. Nothing to do!")
    else:
        ship_actions.update_product_channel_version(shipit_config, product, channel, version)


# ACTION_MAP {{{1
ACTION_MAP = {
    "mark-as-shipped": mark_as_shipped_action,
    "create-new-release": create_new_release_action,
    "update-product-channel-version": update_product_channel_version_action,
}


def get_default_config():
    cwd = os.getcwd()
    parent_dir = os.path.dirname(cwd)
    data_dir = os.path.join(os.path.dirname(__file__), "data")

    return {
        "work_dir": os.path.join(parent_dir, "work_dir"),
        "verbose": False,
        "mark_as_shipped_schema_file": os.path.join(data_dir, "mark_as_shipped_task_schema.json"),
        "create_new_release_schema_file": os.path.join(data_dir, "create_new_release_task_schema.json"),
    }


def main(config_path=None):
    client.sync_main(async_main, config_path=config_path, default_config=get_default_config(), should_validate_task=False)


__name__ == "__main__" and main()
