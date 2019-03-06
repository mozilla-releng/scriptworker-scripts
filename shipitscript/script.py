#!/usr/bin/env python3
""" ShipIt main script
"""
import logging
import os

from scriptworker import client

from shipitscript import ship_actions
from shipitscript.task import (
    validate_task_schema, get_ship_it_instance_config_from_scope,
    get_task_action,
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
    if 'api_root' in context.ship_it_instance_config:
        ship_actions.mark_as_shipped(context.ship_it_instance_config,
                                     release_name)
    if 'api_root_v2' in context.ship_it_instance_config:
        ship_actions.mark_as_shipped_v2(context.ship_it_instance_config,
                                        release_name)


def mark_as_started_action(context):
    """Action to perform is to tell Ship-it v1 API that a release has started.
    This is useful to simulate the RelMan human `Do eet` action."""
    # process the values from the task payload?
    # add a new sip_action to hack the HTML
    payload = context.task['payload']
    release_name = payload['release_name']

    data = dict(
        product=payload['product'],
        version=payload['version'],
        buildNumber=payload['build_number'],
        branch=payload['branch'],
        mozillaRevision=payload['revision'],
        l10nChangesets=payload['l10n_changesets'],
        partials=payload['partials'],
    )

    log.info('Marking the release as started in Ship-it v1 ...')
    ship_actions.mark_as_started(context.ship_it_instance_config,
                                 release_name, data)


# ACTION_MAP {{{1
ACTION_MAP = {
    'mark-as-shipped': mark_as_shipped_action,
    'mark-as-started': mark_as_started_action,
}


def get_default_config():
    cwd = os.getcwd()
    parent_dir = os.path.dirname(cwd)
    data_dir = os.path.join(os.path.dirname(__file__), 'data')

    return {
        'work_dir': os.path.join(parent_dir, 'work_dir'),
        'verbose': False,
        'mark_as_shipped_schema_file': os.path.join(data_dir, 'mark_as_shipped_task_schema.json'),
        'mark_as_started_schema_file': os.path.join(data_dir, 'mark_as_started_task_schema.json'),
    }


def main(config_path=None):
    client.sync_main(async_main, config_path=config_path,
                     default_config=get_default_config(),
                     should_validate_task=False)


__name__ == '__main__' and main()
