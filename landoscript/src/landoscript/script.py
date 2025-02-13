import logging
import os.path

import aiohttp
import scriptworker.client

from landoscript import lando
from landoscript.actions import version_bump
from landoscript.github import GithubClient
from scriptworker_client.github import extract_github_repo_owner_and_name

log = logging.getLogger(__name__)


def get_default_config(base_dir="") -> dict:
    base_dir = base_dir or os.path.dirname(os.getcwd())
    default_config = {
        "work_dir": os.path.join(base_dir, "work_dir"),
        "artifact_dir": os.path.join(base_dir, "artifact_dir"),
        "schema_file": os.path.join(os.path.dirname(__file__), "data", "landoscript_task_schema.json"),
    }
    return default_config


async def async_main(context):
    config = context.config
    payload = context.task["payload"]
    artifact_dir = config["artifact_dir"]
    public_artifact_dir = os.path.join(artifact_dir, "public", "build")
    owner, repo = extract_github_repo_owner_and_name(payload["source_repo"])

    os.makedirs(public_artifact_dir)

    lando_actions = []
    async with GithubClient(context.config["github_config"], owner, repo) as gh_client:
        for action in payload["actions"]:
            if action == "version_bump":
                version_bump_action = await version_bump.run(
                    gh_client,
                    public_artifact_dir,
                    payload["branch"],
                    payload["version_bump_info"],
                    payload.get("dontbuild", False),
                    payload.get("ignore_closed_tree", False),
                )
                if version_bump_action:
                    lando_actions.append(version_bump_action)

    if lando_actions:
        log.info("Submitting lando actions:")
        for la in lando_actions:
            log.info(la)

        async with aiohttp.ClientSession() as session:
            status_url = await lando.submit(
                session, config["lando_api"], payload["source_repo"], payload["branch"], lando_actions, config["sleeptime_callback"]
            )
            await lando.poll_until_complete(session, config["poll_time"], status_url)
    else:
        log.info("No lando actions to submit!")


def main(config_path: str = ""):
    return scriptworker.client.sync_main(async_main, config_path=config_path, default_config=get_default_config())


if __name__ == "__main__":
    main()
