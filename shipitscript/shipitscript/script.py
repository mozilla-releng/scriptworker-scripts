#!/usr/bin/env python3
""" ShipIt main script
"""
import logging
import os

from scriptworker import client

from shipitscript import ship_actions
from shipitscript.task import (
    get_ship_it_instance_config_from_scope,
    get_task_action,
    validate_task_schema,
    are_releases_disabled,
    get_most_recent_shipped_revision,
    get_next_release_version,
    get_shippable_revision,
    get_buildnum_from_version,
    create_new_release,
    trigger_release_phase,
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


def create_new_release(context):
    """Determine if there is a shippable release and create it if so in Shipit """
    payload = context.task['payload']
    # TODO determine product, channel, repo, phase from payload
    product = None
    channel = None
    repo = None
    phase = None  # release phase we want to trigger

    log.info('Determining if shipit has automatic releases disabled')
    are_releases_disabled(product, channel)
    log.info('Determining most recent shipped revision and next version and buildnum to release')
    last_shipped_revision = get_most_recent_shipped_revision(product, channel)
    next_version = get_next_release_version(product, channel)
    log.info('Ensuring next version is a new version and not a buildnum increment')
    if get_buildnum_from_version(next_version) != 1:
        # TODO quit early, mark task as green though
        pass
    log.info('Determining most recent shippable revision')
    shippable_revision = get_shippable_revision(repo)
    if not shippable_revision:
        # TODO quit early, mark task as green though
        pass
    log.info('create a new release')
    release = create_new_release(product, repo, next_version, shippable_revision)
    trigger_release_phase(release)


# ACTION_MAP {{{1
ACTION_MAP = {
    'mark-as-shipped': mark_as_shipped_action,
    'create-new-release': create_new_release,
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
    }


def main(config_path=None):
    client.sync_main(
        async_main,
        config_path=config_path,
        default_config=get_default_config(),
        should_validate_task=False,
    )


__name__ == '__main__' and main()
