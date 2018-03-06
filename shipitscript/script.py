#!/usr/bin/env python3
""" ShipIt main script
"""
import logging

from scriptworker.client import get_task, sync_main, validate_task_schema

from shipitscript.ship_actions import mark_as_shipped
from shipitscript.task import get_ship_it_instance_config_from_scope


log = logging.getLogger(__name__)


async def async_main(context):
    context.task = get_task(context.config)
    log.info('Validating task definition...')
    validate_task_schema(context)
    ship_it_instance_config = get_ship_it_instance_config_from_scope(context)

    release_name = context.task['payload']['release_name']
    mark_as_shipped(ship_it_instance_config, release_name)
    log.info('Done!')


__name__ == '__main__' and sync_main(async_main)
