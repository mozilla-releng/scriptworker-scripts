#!/usr/bin/env python3
""" Bitrise main script
"""
import asyncio
import logging
import os

from bitrisescript.bitrise import BitriseClient, run_build
from bitrisescript.task import get_artifact_dir, get_bitrise_app, get_bitrise_workflows, get_build_params
from scriptworker_client.client import sync_main

log = logging.getLogger(__name__)


async def async_main(config, task):
    app = get_bitrise_app(config, task)
    log.info(f"Bitrise app: '{app}'")

    artifact_dir = get_artifact_dir(config, task)
    build_params = get_build_params(task)

    futures = []
    for workflow in get_bitrise_workflows(config, task):
        build_params["workflow_id"] = workflow
        futures.append(run_build(artifact_dir, **build_params))

    client = None
    try:
        client = BitriseClient()
        client.set_auth(config["bitrise"]["access_token"])
        await client.set_app_prefix(app)
        await asyncio.gather(*futures)
    finally:
        if client:
            await client.close()

    log.info("Done!")


def get_default_config():
    cwd = os.getcwd()
    parent_dir = os.path.dirname(cwd)

    return {
        "work_dir": os.path.join(parent_dir, "work_dir"),
        "verbose": False,
    }


def main(config_path=None):
    sync_main(async_main, config_path=config_path, default_config=get_default_config(), should_verify_task=False)


if __name__ == "__main__":
    main()
