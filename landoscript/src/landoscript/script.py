import json
import logging
import os.path

import aiohttp
import scriptworker.client
from scriptworker.exceptions import TaskVerificationError
from scriptworker.utils import calculate_sleep_time

import taskcluster
from landoscript import lando, treestatus
from landoscript.actions import android_l10n_import, android_l10n_sync, l10n_bump, merge_day, tag, version_bump
from scriptworker_client.github import extract_github_repo_owner_and_name
from scriptworker_client.github_client import GithubClient
from scriptworker_client.utils import retry_async

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


def sanity_check_payload(payload, scopes, lando_repo):
    """Additional verification past what the task schema does."""
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


async def process_actions(session, context, owner, repo, public_artifact_dir, branch) -> list[lando.LandoAction]:
    config = context.config
    payload = context.task["payload"]
    lando_repo = payload["lando_repo"]
    dontbuild = payload.get("dontbuild", False)
    ignore_closed_tree = payload.get("ignore_closed_tree", True)

    is_tree_open = True
    if not ignore_closed_tree:
        is_tree_open = await treestatus.is_tree_open(session, config["treestatus_url"], lando_repo, config.get("sleeptime_callback"))

    lando_actions: list[lando.LandoAction] = []

    async with GithubClient(context.config["github_config"], owner, repo) as gh_client:
        for action in payload["actions"]:
            log.info(f"processing action: {action}")

            if action == "version_bump":
                version_bump_actions = await version_bump.run(
                    gh_client,
                    public_artifact_dir,
                    branch,
                    [version_bump.VersionBumpInfo(**payload["version_bump_info"])],
                )
                if version_bump_actions:
                    lando_actions.extend(version_bump_actions)
            elif action == "tag":
                if "hg_repo_url" not in payload["tag_info"]:
                    raise TaskVerificationError("must provide hg_repo_url!")
                tag_actions = await tag.run(session, tag.HgTagInfo(**payload["tag_info"]))
                lando_actions.extend(tag_actions)
            elif action == "merge_day":
                merge_day_actions = await merge_day.run(
                    session, gh_client, context.config["github_config"], public_artifact_dir, merge_day.MergeInfo.from_payload_data(payload["merge_info"])
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
                if l10n_bump_actions:
                    lando_actions.extend(l10n_bump_actions)
            elif action == "android_l10n_import":
                android_l10n_import_info = android_l10n_import.AndroidL10nImportInfo.from_payload_data(payload["android_l10n_import_info"])
                import_actions = await android_l10n_import.run(
                    gh_client, context.config["github_config"], public_artifact_dir, android_l10n_import_info, branch
                )
                if import_actions:
                    lando_actions.extend(import_actions)
            elif action == "android_l10n_sync":
                if not is_tree_open:
                    log.info("Treestatus is closed; skipping android l10n sync.")
                    continue

                android_l10n_sync_info = android_l10n_sync.AndroidL10nSyncInfo.from_payload_data(payload["android_l10n_sync_info"])
                import_actions = await android_l10n_sync.run(gh_client, public_artifact_dir, android_l10n_sync_info, branch)
                if import_actions:
                    lando_actions.extend(import_actions)

            log.info("finished processing action")

    return lando_actions


async def get_status_url_from_earlier_run(session: aiohttp.ClientSession) -> str | None:
    root_url = os.environ.get("TASKCLUSTER_ROOT_URL")
    task_id = os.environ.get("TASK_ID")
    run_id = os.environ.get("RUN_ID")
    if not root_url or not task_id or not run_id:
        log.warning("Taskcluster environment variables are not set; not trying to resume an earlier run!")
        return

    queue = taskcluster.Queue(options={"rootUrl": root_url})
    taskStatus = queue.status(task_id)
    assert taskStatus
    runs = taskStatus.get("status", {}).get("runs")
    assert runs is not None
    run_id = int(run_id)
    while run_id > 0:
        run_id -= 1
        try:
            # if the newest, potentially usable task has actually failed outright
            # don't re-use the status. this ensures that reruns, eg: after a
            # server side issue with Lando has been resolved, behave as expected.
            # it is OK to re-use status for other states (typically this would be
            # "exception", but if a forced rerun happens on a "completed" task
            # we ought to not to submit a new request either).
            if runs[run_id]["state"] == "failed":
                return

            # `getArtifact` has built in retries, and automatically raises on failure
            artifactInfo = queue.getArtifact(task_id, run_id, "public/build/lando-status.txt")
            assert artifactInfo
            url = artifactInfo.get("url")
            assert url
            resp = await retry_async(
                session.get,
                args=(str(url),),
                kwargs={"raise_for_status": True},
                attempts=5,
                retry_exceptions=aiohttp.ClientResponseError,
                sleeptime_callback=calculate_sleep_time,
            )
            return (await resp.content.read()).decode()
        except taskcluster.TaskclusterRestFailure as e:
            if e.status_code >= 500:
                log.error("taskcluster is unavailable...cannot continue!")
                raise
            # error is 4xx; most likely, the artifact doesn't exist...
            # carry on and try the next latest run


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

        # pull owner, repo, and branch from config
        repo_url, branch = await lando.get_repo_info(session, lando_api, lando_token, lando_repo)
        owner, repo = extract_github_repo_owner_and_name(repo_url)
        log.info(f"Got owner: {owner}, repo: {repo}, branch: {branch}")

        sanity_check_payload(payload, scopes, lando_repo)

        os.makedirs(public_artifact_dir)

        # check for status url in earlier run
        status_url = await get_status_url_from_earlier_run(session)

        if status_url:
            log.info(f"Polling status url from earlier run: {status_url}")
            await lando.poll_until_complete(session, lando_token, config["poll_time"], status_url)
        else:
            lando_actions = await process_actions(session, context, owner, repo, public_artifact_dir, branch)

            if lando_actions:
                with open(os.path.join(public_artifact_dir, "lando-actions.json"), "w+") as f:
                    f.write(json.dumps(lando_actions, indent=2))

                if payload.get("dry_run", False):
                    log.info("Dry run...would've submitted lando actions:")
                    lando.print_actions(lando_actions)
                else:
                    log.info("Not a dry run...submitting lando actions:")
                    lando.print_actions(lando_actions)

                    status_url = await lando.submit(session, lando_api, lando_token, lando_repo, lando_actions, config.get("sleeptime_callback"))
                    with open(os.path.join(public_artifact_dir, "lando-status.txt"), "w+") as f:
                        f.write(status_url)

                    await lando.poll_until_complete(session, lando_token, config["poll_time"], status_url)
            else:
                log.info("No lando actions to submit!")


def main(config_path=None):
    # gql is extremely noisy at our typical log level (it logs all request and response bodies)
    logging.getLogger("gql").setLevel(logging.WARNING)
    return scriptworker.client.sync_main(async_main, config_path=config_path, default_config=get_default_config())


if __name__ == "__main__":
    main()
