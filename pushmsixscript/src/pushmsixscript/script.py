#!/usr/bin/env python3
""" Push msix Script main script
"""
import logging
import os

from scriptworker_client import client

from pushmsixscript import artifacts, manifest, microsoft_store, task

log = logging.getLogger(__name__)


async def async_main(config, task_dict):
    msix_file_paths = artifacts.get_msix_file_paths(config, task_dict)
    for msix_file_path in msix_file_paths:
        log.info(f"found msix at {msix_file_path}")
        manifest.verify_msix(msix_file_path)

    channel = task.get_msix_channel(config, task_dict)
    _log_warning_forewords(config, channel)

    payload = task_dict.get("payload")
    if payload:
        publish_mode = payload.get("publishMode")
    else:
        publish_mode = None

    microsoft_store.push(config, msix_file_paths, channel, publish_mode)


def _log_warning_forewords(config, channel):
    if not task.is_allowed_to_push_to_microsoft_store(config, channel):
        log.warning("Insufficient rights to reach Microsoft Store: *All* requests will be mocked.")


def get_default_config(base_dir=None):
    base_dir = base_dir or os.path.dirname(os.getcwd())
    default_config = {
        "work_dir": os.path.join(base_dir, "work_dir"),
        "schema_file": os.path.join(os.path.dirname(__file__), "data", "push_msix_task_schema.json"),
        "verbose": False,
    }
    return default_config


def main(config_path=None):
    return client.sync_main(async_main, config_path=config_path, default_config=get_default_config())


__name__ == "__main__" and main()
