#!/usr/bin/env python3
""" ShipIt main script
"""
import logging
import os

from scriptworker import client

from shipitscript import ship_actions, task


log = logging.getLogger(__name__)


async def async_main(context):
    ship_it_instance_config = task.get_ship_it_instance_config_from_scope(context)
    release_name = context.task['payload']['release_name']
    ship_actions.mark_as_shipped(ship_it_instance_config, release_name)
    log.info('Done!')


def get_default_config():
    cwd = os.getcwd()
    parent_dir = os.path.dirname(cwd)

    return {
        'work_dir': os.path.join(parent_dir, 'work_dir'),
        'schema_file': os.path.join(cwd, 'shipitscript', 'data', 'shipit_task_schema.json'),
        'verbose': False,
    }


def main(config_path=None):
    client.sync_main(async_main, config_path=config_path, default_config=get_default_config())


__name__ == '__main__' and main()
