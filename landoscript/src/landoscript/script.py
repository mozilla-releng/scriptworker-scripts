import logging
import os.path

import aiohttp
import scriptworker.client

from landoscript import lando
from landoscript.actions import tag, version_bump
from scriptworker_client.github_client import GithubClient

log = logging.getLogger(__name__)


def get_default_config(base_dir: str = "") -> dict:
    base_dir = base_dir or os.path.dirname(os.getcwd())
    default_config = {
        "work_dir": os.path.join(base_dir, "work_dir"),
        "artifact_dir": os.path.join(base_dir, "artifact_dir"),
        "schema_file": os.path.join(os.path.dirname(__file__), "data", "landoscript_task_schema.json"),
    }
    return default_config


def validate_scopes(scopes: set, lando_repo: str, actions: list[str]):
    expected_scopes = {
        f"project:releng:lando:repo:{lando_repo}",
        *[f"project:releng:lando:action:{action}" for action in actions],
    }
    missing = expected_scopes - scopes
    if missing:
        raise scriptworker.client.TaskVerificationError(f"required scope(s) not present: {', '.join(missing)}")


# `context` is kept explicitly untyped because all of its members are typed as
# Optional. This never happens in reality (only in tests), but as things stand
# at the time of writing, it means we need noisy and unnecessary None checking
# to avoid linter complaints.
async def async_main(context):
    config = context.config
    payload = context.task["payload"]
    scopes = set(context.task["scopes"])
    artifact_dir = config["artifact_dir"]
    public_artifact_dir = os.path.join(artifact_dir, "public", "build")

    # Note: `lando_repo` is not necessarily the same as the repository's name
    # on Github.
    lando_repo = payload["lando_repo"]

    # pull owner, repo, and branch from config
    # TODO: replace this with a lookup through the lando API when that API exists
    log.info(f"looking up repository details for lando repo: {lando_repo}")
    repo_details = context.config["lando_name_to_github_repo"][lando_repo]
    owner = repo_details["owner"]
    repo = repo_details["repo"]
    branch = repo_details["branch"]
    log.info(f"Got owner: {owner}, repo: {repo}, branch: {branch}")

    # validate scopes - these raise if there's any scope issues
    validate_scopes(scopes, lando_repo, payload["actions"])

    os.makedirs(public_artifact_dir)

    lando_actions: list[lando.LandoAction] = []
    async with GithubClient(context.config["github_config"], owner, repo) as gh_client:
        for action in payload["actions"]:
            log.info(f"processing action: {action}")

            if action == "version_bump":
                version_bump_action = await version_bump.run(
                    gh_client,
                    public_artifact_dir,
                    branch,
                    payload["version_bump_info"],
                    payload.get("dontbuild", False),
                )
                # sometimes version bumps are no-ops
                if version_bump_action:
                    lando_actions.append(version_bump_action)
            elif action == "tag":
                tag_actions = tag.run(payload["tags"])
                lando_actions.extend(tag_actions)

            log.info("finished processing action")

    if lando_actions:
        if payload.get("dry_run", False):
            log.info("dry run...would've submitted lando actions:")
            for la in lando_actions:
                log.info(la)
        else:
            log.info("not a dry run...submitting lando actions:")
            for la in lando_actions:
                log.info(la)

            async with aiohttp.ClientSession() as session:
                status_url = await lando.submit(session, config["lando_api"], lando_repo, lando_actions, config["sleeptime_callback"])
                await lando.poll_until_complete(session, config["poll_time"], status_url)
    else:
        log.info("no lando actions to submit!")


def main(config_path: str = ""):
    return scriptworker.client.sync_main(async_main, config_path=config_path, default_config=get_default_config())


if __name__ == "__main__":
    main()
