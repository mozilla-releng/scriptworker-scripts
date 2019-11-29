#!/usr/bin/env python3
""" ShipIt main script
"""
import logging
import os
import sys

from scriptworker import client

from shipitscript import ship_actions
from shipitscript.task import (
    get_ship_it_instance_config_from_scope,
    get_task_action,
    validate_task_schema,
)

log = logging.getLogger(__name__)


async def async_main(context):
    validate_task_schema(context)

    context.ship_it_instance_config = get_ship_it_instance_config_from_scope(context)
    context.action = get_task_action(context)

    # action has already been validated
    ACTION_MAP[context.action](context)
    log.info('Success!')


def mark_as_shipped_action(context):
    """Action to perform is to tell Ship-it API that a release can be marked
    as shipped"""
    release_name = context.task['payload']['release_name']

    log.info('Marking the release as shipped ...')
    ship_actions.mark_as_shipped_v2(context.ship_it_instance_config, release_name)


def create_new_release_action(context):
    """Determine if there is a shippable release and create it if so in Shipit"""
    payload = context.task['payload']
    shipit_config = context.ship_it_instance_config
    product = payload['product']
    branch = payload['branch']
    phase = payload['phase']
    version = payload['version']
    cron_revision = payload['cron_revision']  # rev that cron triggered on

    log.info('Determining most recent shipped revision based off we released')
    last_shipped_revision = ship_actions.get_most_recent_shipped_revision(
        shipit_config, product, branch,
    )
    if not last_shipped_revision:
        log.error("Something is broken under the sun if no shipped revision")
        sys.exit(1)
    log.info('Last shipped revision is {last_shipped_revision}')

    log.info('Determining most recent shippable revision')
    shippable_revision = ship_actions.get_shippable_revision(
        branch, last_shipped_revision, cron_revision,
    )
    if not shippable_revision:
        log.info("No valid shippable revisison found, silent exit ...")
        return
    log.info('The shippable revision found is {shippable_revision}')

    log.info('Starting a new release in Ship-it ...')
    ship_actions.start_new_release(
        shipit_config, product, branch, version, shippable_revision, phase,
    )


# ACTION_MAP {{{1
ACTION_MAP = {
    'mark-as-shipped': mark_as_shipped_action,
    'create-new-release': create_new_release_action,
}


def get_default_config():
    cwd = os.getcwd()
    parent_dir = os.path.dirname(cwd)
    data_dir = os.path.join(os.path.dirname(__file__), 'data')

    return {
        'work_dir': os.path.join(parent_dir, 'work_dir'),
        'verbose': False,
        'mark_as_shipped_schema_file': os.path.join(
            data_dir, 'mark_as_shipped_task_schema.json'
        ),
        'create_new_release_schema_file': os.path.join(
            data_dir, 'create_new_release_task_schema.json'
        ),
    }


def main(config_path=None):
    client.sync_main(
        async_main,
        config_path=config_path,
        default_config=get_default_config(),
        should_validate_task=False,
    )


__name__ == '__main__' and main()
