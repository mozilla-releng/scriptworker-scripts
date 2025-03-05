import logging
import os.path

import aiohttp
import scriptworker.client

from landoscript.actions import version_bump
from landoscript.github import GithubClient
from landoscript.types import Context
from scriptworker_client.github import extract_github_repo_owner_and_name

log = logging.getLogger(__name__)


def get_default_config(base_dir: str = "") -> dict:
    base_dir = base_dir or os.path.dirname(os.getcwd())
    default_config = {
        "work_dir": os.path.join(base_dir, "work_dir"),
        "artifact_dir": os.path.join(base_dir, "artifact_dir"),
        "schema_file": os.path.join(os.path.dirname(__file__), "data", "landoscript_task_schema.json"),
    }
    return default_config


async def async_main(context: Context):
    config = context.config
    payload = context.task["payload"]
    owner, repo = extract_github_repo_owner_and_name(payload["source_repo"])

    async with aiohttp.ClientSession() as session:
        async with GithubClient(context.config["github_config"], owner, repo) as gh_client:
            for action in payload["actions"]:
                if action == "version_bump":
                    await version_bump.run(
                        config,
                        gh_client,
                        session,
                        payload["source_repo"],
                        payload["branch"],
                        payload["version_bump_info"],
                        payload.get("dontbuild", False),
                        payload.get("ignore_closed_tree", False),
                    )


def main(config_path: str = ""):
    return scriptworker.client.sync_main(async_main, config_path=config_path, default_config=get_default_config())


if __name__ == "__main__":
    main()
