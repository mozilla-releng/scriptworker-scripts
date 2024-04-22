#!/usr/bin/env python3
"""Bitrise main script"""

import asyncio
import logging
import os

from bitrisescript.bitrise import BitriseClient, find_running_build, get_running_builds, run_build, wait_and_download_workflow_log
from bitrisescript.task import get_artifact_dir, get_bitrise_app, get_bitrise_workflows, get_build_params
from scriptworker_client.client import sync_main

log = logging.getLogger(__name__)


async def async_main(config, task):
    app = get_bitrise_app(config, task)
    log.info(f"Bitrise app: '{app}'")

    artifact_dir = get_artifact_dir(config, task)

    client = None
    try:
        client = BitriseClient()
        client.set_auth(config["bitrise"]["access_token"])

        futures = []
        branch = task["payload"].get("global_params", {}).get("branch", "main")
        for workflow in get_bitrise_workflows(config, task):
            running_builds = await get_running_builds(workflow, branch=branch)
            build_params_list = get_build_params(task, workflow)
            for build_params in build_params_list:
                existing_build_slug = find_running_build(running_builds, build_params)
                if existing_build_slug:
                    futures.append(wait_and_download_workflow_log(artifact_dir, existing_build_slug))
                else:
                    futures.append(run_build(artifact_dir, **build_params))

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
