import logging
import os.path

import aiohttp
import scriptworker.client
from scriptworker.exceptions import TaskVerificationError

from landoscript import lando, treestatus
from landoscript.actions import android_l10n_import, android_l10n_sync, l10n_bump, merge_day, tag, version_bump
from scriptworker_client.github import extract_github_repo_owner_and_name
from scriptworker_client.github_client import GithubClient

log = logging.getLogger(__name__)


def get_default_config(base_dir: str = "") -> dict:
    base_dir = base_dir or os.path.dirname(os.getcwd())
    default_config = {
        "work_dir": os.path.join(base_dir, "work_dir"),
        "artifact_dir": os.path.join(base_dir, "artifact_dir"),
        "schema_file": os.path.join(os.path.dirname(__file__), "data", "landoscript_task_schema.json"),
        "poll_time": 30,
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


def sanity_check_payload(payload):
    pass


# `context` is kept explicitly untyped because all of its members are typed as
# Optional. This never happens in reality (only in tests), but as things stand
# at the time of writing, it means we need noisy and unnecessary None checking
# to avoid linter complaints.
async def async_main(context):
    async with aiohttp.ClientSession() as session:
        config = context.config
        payload = context.task["payload"]
        scopes = set(context.task["scopes"])
        artifact_dir = config["artifact_dir"]
        public_artifact_dir = os.path.join(artifact_dir, "public", "build")

        # Note: `lando_repo` is not necessarily the same as the repository's name
        # on Github.
        lando_api = config["lando_api"]
        lando_token = config["lando_token"]
        lando_repo = payload["lando_repo"]
        dontbuild = payload.get("dontbuild", False)
        ignore_closed_tree = payload.get("ignore_closed_tree", True)

        # pull owner, repo, and branch from config
        repo_url, branch = await lando.get_repo_info(session, lando_api, lando_token, lando_repo)
        owner, repo = extract_github_repo_owner_and_name(repo_url)
        log.info(f"Got owner: {owner}, repo: {repo}, branch: {branch}")

        # validate scopes - these raise if there's any scope issues
        validate_scopes(scopes, lando_repo, payload["actions"])
        if len(payload["actions"]) < 1:
            raise TaskVerificationError("must provide at least one action!")

        if not any([action == "l10n_bump" for action in payload["actions"]]):
            if "dontbuild" in payload:
                raise TaskVerificationError("dontbuild is only respected in l10n_bump!")

        if not any([action in ("android_l10n_sync", "l10n_bump") for action in payload["actions"]]):
            if "ignore_closed_tree" in payload:
                raise TaskVerificationError("ignore_closed_tree is only respected in l10n_bump and android_l10n_sync!")

        os.makedirs(public_artifact_dir)

        is_tree_open = True
        if not ignore_closed_tree:
            is_tree_open = await treestatus.is_tree_open(session, config["treestatus_url"], lando_repo, config.get("sleeptime_callback"))

        lando_actions: list[lando.LandoAction] = []
        async with GithubClient(context.config["github_config"], owner, repo) as gh_client:
            for action in payload["actions"]:
                log.info(f"processing action: {action}")

                if action == "version_bump":
                    version_bump_action = await version_bump.run(
                        gh_client,
                        public_artifact_dir,
                        branch,
                        [version_bump.VersionBumpInfo(**payload["version_bump_info"])],
                    )
                    # sometimes version bumps are no-ops
                    if version_bump_action:
                        lando_actions.append(version_bump_action)
                elif action == "tag":
                    if "hg_repo_url" not in payload["tag_info"]:
                        raise TaskVerificationError("must provide hg_repo_url!")
                    tag_actions = await tag.run(session, tag.HgTagInfo(**payload["tag_info"]))
                    lando_actions.extend(tag_actions)
                elif action == "merge_day":
                    merge_day_actions = await merge_day.run(
                        session, gh_client, public_artifact_dir, merge_day.MergeInfo.from_payload_data(payload["merge_info"])
                    )
                    lando_actions.extend(merge_day_actions)
                elif action == "l10n_bump":
                    if not is_tree_open:
                        log.info("Treestatus is closed; skipping l10n bump.")
                        continue

                    l10n_bump_info = [l10n_bump.L10nBumpInfo.from_payload_data(lbi) for lbi in payload["l10n_bump_info"]]
                    l10n_bump_actions = await l10n_bump.run(
                        gh_client, context.config["github_config"], public_artifact_dir, branch, l10n_bump_info, dontbuild, ignore_closed_tree
                    )
                    # sometimes nothing has changed!
                    if l10n_bump_actions:
                        lando_actions.extend(l10n_bump_actions)
                elif action == "android_l10n_import":
                    android_l10n_import_info = android_l10n_import.AndroidL10nImportInfo.from_payload_data(payload["android_l10n_import_info"])
                    import_action = await android_l10n_import.run(
                        gh_client, context.config["github_config"], public_artifact_dir, android_l10n_import_info, branch
                    )
                    if import_action:
                        lando_actions.append(import_action)
                elif action == "android_l10n_sync":
                    if not is_tree_open:
                        log.info("Treestatus is closed; skipping android l10n sync.")
                        continue

                    android_l10n_sync_info = android_l10n_sync.AndroidL10nSyncInfo.from_payload_data(payload["android_l10n_sync_info"])
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

                status_url = await lando.submit(session, lando_api, lando_token, lando_repo, lando_actions, config.get("sleeptime_callback"))
                await lando.poll_until_complete(session, lando_token, config["poll_time"], status_url)
        else:
            log.info("No lando actions to submit!")


def main(config_path: str = ""):
    # gql is extremely noisy at our typical log level (it logs all request and response bodies)
    logging.getLogger("gql").setLevel(logging.WARNING)
    return scriptworker.client.sync_main(async_main, config_path=config_path, default_config=get_default_config())


if __name__ == "__main__":
    main()
