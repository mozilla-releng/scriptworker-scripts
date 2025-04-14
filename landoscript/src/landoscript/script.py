import logging
import os.path

import aiohttp
import scriptworker.client
from scriptworker.exceptions import TaskVerificationError

from landoscript import lando
from landoscript.actions import android_l10n_import, android_l10n_sync, l10n_bump, merge_day, tag, version_bump
from landoscript.treestatus import is_tree_open
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
    dontbuild = payload.get("dontbuild", False)
    ignore_closed_tree = payload.get("ignore_closed_tree", False)

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
    if len(payload["actions"]) < 1:
        raise TaskVerificationError("must provide at least one action!")

    if not any([action == "l10n_bump" for action in payload["actions"]]):
        if "dontbuild" in payload or "ignore_closed_tree" in payload:
            raise TaskVerificationError("dontbuild and ignore_closed_tree are only respected in l10n_bump!")

    os.makedirs(public_artifact_dir)

    lando_actions: list[lando.LandoAction] = []
    async with aiohttp.ClientSession() as session:
        async with GithubClient(context.config["github_config"], owner, repo) as gh_client:
            for action in payload["actions"]:
                log.info(f"processing action: {action}")

                if action == "version_bump":
                    version_bump_action = await version_bump.run(
                        gh_client,
                        public_artifact_dir,
                        branch,
                        [version_bump.VersionBumpInfo(payload["version_bump_info"])],
                    )
                    # sometimes version bumps are no-ops
                    if version_bump_action:
                        lando_actions.append(version_bump_action)
                elif action == "tag":
                    tag_actions = tag.run(payload["tags"])
                    lando_actions.extend(tag_actions)
                elif action == "merge_day":
                    merge_day_actions = await merge_day.run(gh_client, public_artifact_dir, payload["merge_info"])
                    lando_actions.extend(merge_day_actions)
                elif action == "l10n_bump":
                    if not ignore_closed_tree:
                        # despite `ignore_closed_tree` being at the top level of the
                        # payload, only l10n bumps pay attention to it. we should probably
                        # set it to true for all other actions so we can actually make
                        # this a global check
                        if not await is_tree_open(session, config["treestatus_url"], lando_repo, config["sleeptime_callback"]):
                            log.info("Treestatus is closed; skipping l10n bump.")
                            continue

                    l10n_bump_actions = await l10n_bump.run(
                        gh_client, context.config["github_config"], public_artifact_dir, branch, payload["l10n_bump_info"], dontbuild, ignore_closed_tree
                    )
                    # sometimes nothing has changed!
                    if l10n_bump_actions:
                        lando_actions.extend(l10n_bump_actions)
                elif action == "android_l10n_import":
                    android_l10n_import_info = payload["android_l10n_import_info"]
                    import_action = await android_l10n_import.run(
                        gh_client, context.config["github_config"], public_artifact_dir, android_l10n_import_info, branch
                    )
                    if import_action:
                        lando_actions.append(import_action)
                elif action == "android_l10n_sync":
                    android_l10n_sync_info = payload["android_l10n_sync_info"]
                    import_action = await android_l10n_sync.run(gh_client, public_artifact_dir, android_l10n_sync_info, branch)
                    if import_action:
                        lando_actions.append(import_action)

                log.info("finished processing action")

        if lando_actions:
            if payload.get("dry_run", False):
                log.info("Dry run...would've submitted lando actions:")
                for la in lando_actions:
                    log.info(la)
            else:
                log.info("Not a dry run...submitting lando actions:")
                for la in lando_actions:
                    log.info(la)

                status_url = await lando.submit(session, config["lando_api"], lando_repo, lando_actions, config["sleeptime_callback"])
                await lando.poll_until_complete(session, config["poll_time"], status_url)
        else:
            log.info("No lando actions to submit!")


def main(config_path: str = ""):
    return scriptworker.client.sync_main(async_main, config_path=config_path, default_config=get_default_config())


if __name__ == "__main__":
    main()
