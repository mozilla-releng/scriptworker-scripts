import json
from aiohttp import ClientResponseError
import pytest
from scriptworker.client import STATUSES, TaskVerificationError
from pytest_scriptworker_client import get_files_payload

from landoscript.errors import LandoscriptError, MergeConflictError
from landoscript.script import async_main
from .conftest import (
    assert_lando_submission_response,
    assert_status_response,
    run_test,
    setup_github_graphql_responses,
    setup_test,
    assert_add_commit_response,
)
from .test_tag import assert_tag_response


def assert_success(artifact_dir, req, commit_msg_strings, initial_values, expected_bumps, has_actions=True):
    if has_actions:
        assert (artifact_dir / "public/build/lando-actions.json").exists()
        lando_status = artifact_dir / "public/build/lando-status.json"
        assert lando_status.exists()
        with open(lando_status) as ls:
            status = json.loads(ls.read())
            assert "url" in status
            # for successes, this will be present but empty
            assert "failure_reason" in status

    assert "json" in req.kwargs
    assert "actions" in req.kwargs["json"]
    create_commit_actions = [action for action in req.kwargs["json"]["actions"] if action["action"] == "create-commit"]
    assert len(create_commit_actions) == 1
    action = create_commit_actions[0]

    assert_add_commit_response(action, commit_msg_strings, initial_values, expected_bumps)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,initial_values,expected_bumps,commit_msg_strings,dry_run",
    (
        pytest.param(
            {
                "actions": ["tag", "version_bump"],
                "lando_repo": "repo_name",
                "version_bump_info": {
                    "files": ["browser/config/version.txt"],
                    "next_version": "135.0",
                },
                "tag_info": {
                    "revision": "abcdef123456",
                    "hg_repo_url": "https://hg.testing/repo",
                    "tags": ["RELEASE"],
                },
                "dry_run": True,
            },
            {
                "browser/config/version.txt": "134.0",
            },
            {
                "browser/config/version.txt": "135.0",
            },
            ["Automatic version bump", "NO BUG", "a=release"],
            True,
            id="tag_and_bump_dry_run",
        ),
        pytest.param(
            {
                "actions": ["tag", "version_bump"],
                "lando_repo": "repo_name",
                "version_bump_info": {
                    "files": ["browser/config/version.txt"],
                    "next_version": "135.0",
                },
                "tag_info": {
                    "revision": "abcdef123456",
                    "hg_repo_url": "https://hg.testing/repo",
                    "tags": ["RELEASE"],
                },
            },
            {
                "browser/config/version.txt": "134.0",
            },
            {
                "browser/config/version.txt": "135.0",
            },
            ["Automatic version bump", "NO BUG", "a=release"],
            False,
            id="tag_and_bump",
        ),
    ),
)
async def test_tag_and_bump(aioresponses, github_installation_responses, context, payload, dry_run, initial_values, expected_bumps, commit_msg_strings):
    setup_github_graphql_responses(aioresponses, get_files_payload(initial_values))

    tag_info = payload["tag_info"]
    git_commit = "ghijkl654321"
    aioresponses.get(
        f"{tag_info['hg_repo_url']}/json-rev/{tag_info['revision']}",
        status=200,
        payload={"git_commit": git_commit},
    )

    def assert_func(req):
        assert_success(context.config["artifact_dir"], req, commit_msg_strings, initial_values, expected_bumps)
        assert_tag_response(req, tag_info, git_commit)
        assert (context.config["artifact_dir"] / "public/build/version-bump.diff").exists()

    await run_test(aioresponses, github_installation_responses, context, payload, payload["actions"], not dry_run, assert_func)


@pytest.mark.asyncio
async def test_tag_and_bump_with_race_returns_intermittent_task(aioresponses, github_installation_responses, context):
    """Tests to ensure that when two simultaneously running version bump tasks
    race with each other, and we've lost the race, that we fail with intermittent
    task to force a retry. See https://bugzilla.mozilla.org/show_bug.cgi?id=1966092
    for a real world example."""
    payload = {
        "actions": ["tag", "version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": ["browser/config/version.txt"],
            "next_version": "135.0",
        },
        "tag_info": {
            "revision": "abcdef123456",
            "hg_repo_url": "https://hg.testing/repo",
            "tags": ["RELEASE"],
        },
    }
    initial_values = {
        "browser/config/version.txt": "134.0",
    }
    setup_github_graphql_responses(aioresponses, get_files_payload(initial_values))

    tag_info = payload["tag_info"]
    git_commit = "ghijkl654321"
    aioresponses.get(
        f"{tag_info['hg_repo_url']}/json-rev/{tag_info['revision']}",
        status=200,
        payload={"git_commit": git_commit},
    )

    submit_uri, status_uri, job_id, scopes = setup_test(aioresponses, github_installation_responses, context, payload, ["tag", "version_bump"], "repo_name")

    aioresponses.post(submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"})

    aioresponses.get(
        status_uri,
        status=200,
        payload={
            "job_id": job_id,
            "status_url": str(status_uri),
            "message": "Job is in the FAILED state.",
            "created_at": "2025-03-08T12:25:00Z",
            "status": "FAILED",
            "error": "Merge conflict while creating commit in create-commit, action #1.\n\nChecking patch browser/config/version.txt...\nerror: while searching for:\n138.0.3\n\nerror: patch failed: browser/config/version.txt:1\nChecking patch browser/config/version_display.txt...\nerror: while searching for:\n138.0.3\n\nerror: patch failed: browser/config/version_display.txt:1\nChecking patch config/milestone.txt...\nerror: while searching for:\n# hardcoded milestones in the tree from these two files.\n#--------------------------------------------------------\n\n138.0.3\n\nerror: patch failed: config/milestone.txt:10\nChecking patch mobile/android/version.txt...\nerror: while searching for:\n138.0.3\n\nerror: patch failed: mobile/android/version.txt:1\nApplying patch browser/config/version.txt with 1 reject...\nRejected hunk #1.\nApplying patch browser/config/version_display.txt with 1 reject...\nRejected hunk #1.\nApplying patch config/milestone.txt with 1 reject...\nRejected hunk #1.\nApplying patch mobile/android/version.txt with 1 reject...\nRejected hunk #1.\n",
        },
    )

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised MergeConflictError"
    except MergeConflictError as e:
        assert e.exit_code == STATUSES["intermittent-task"]
        pass


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,initial_values,expected_bumps,commit_msg_strings",
    (
        pytest.param(
            {
                "actions": ["version_bump"],
                "lando_repo": "repo_name",
                "version_bump_info": {
                    "files": ["browser/config/version.txt"],
                    "next_version": "135.0",
                },
            },
            {
                "browser/config/version.txt": "134.0",
            },
            {
                "browser/config/version.txt": "135.0",
            },
            ["Automatic version bump", "NO BUG", "a=release"],
            id="one_file",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "lando_repo": "repo_name",
                "version_bump_info": {
                    "files": [
                        "browser/config/version.txt",
                        "browser/config/version_display.txt",
                        "config/milestone.txt",
                        "mobile/android/version.txt",
                    ],
                    "next_version": "135.0",
                },
            },
            {
                "browser/config/version.txt": "134.0",
                "browser/config/version_display.txt": "134.0",
                "config/milestone.txt": "134.0",
                "mobile/android/version.txt": "134.0",
            },
            {
                "browser/config/version.txt": "135.0",
                "browser/config/version_display.txt": "135.0",
                "config/milestone.txt": "135.0",
                "mobile/android/version.txt": "135.0",
            },
            ["Automatic version bump", "NO BUG", "a=release"],
            id="many_files",
        ),
    ),
)
async def test_success_with_retries(aioresponses, github_installation_responses, context, payload, initial_values, expected_bumps, commit_msg_strings):
    submit_uri, status_uri, job_id, scopes = setup_test(aioresponses, github_installation_responses, context, payload, ["version_bump"])
    setup_github_graphql_responses(aioresponses, get_files_payload(initial_values))

    aioresponses.post(submit_uri, status=500)
    aioresponses.post(submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"})

    aioresponses.get(status_uri, status=202, payload={"status": "pending", "job_id": job_id, "message": "foo", "started_at": "2025-03-08T12:25:00Z"})
    aioresponses.get(
        status_uri,
        status=200,
        payload={
            "commits": ["abcdef123"],
            "push_id": job_id,
            "status": "LANDED",
        },
    )

    context.task = {"payload": payload, "scopes": scopes}
    await async_main(context)

    req = assert_lando_submission_response(aioresponses.requests, submit_uri, attempts=2)
    assert_success(context.config["artifact_dir"], req, commit_msg_strings, initial_values, expected_bumps)
    assert_status_response(aioresponses.requests, status_uri, attempts=2)
    assert (context.config["artifact_dir"] / "public/build/version-bump.diff").exists()


@pytest.mark.asyncio
async def test_no_actions(aioresponses, github_installation_responses, context):
    payload = {
        "actions": [],
        "lando_repo": "repo_name",
    }
    await run_test(
        aioresponses, github_installation_responses, context, payload, ["tag"], err=TaskVerificationError, errmsg="must provide at least one action!"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scopes,missing",
    (
        pytest.param(
            [
                "project:releng:lando:action:tag",
                "project:releng:lando:action:version_bump",
            ],
            [
                "project:releng:lando:repo:repo_name",
            ],
            id="missing_repo_scope",
        ),
        pytest.param(
            [
                "project:releng:lando:repo:repo_name",
                "project:releng:lando:action:tag",
            ],
            [
                "project:releng:lando:action:version_bump",
            ],
            id="missing_one_action_scope",
        ),
        pytest.param(
            [
                "project:releng:lando:repo:repo_name",
            ],
            [
                "project:releng:lando:action:tag",
                "project:releng:lando:action:version_bump",
            ],
            id="missing_two_action_scopes",
        ),
        pytest.param(
            [],
            [
                "project:releng:lando:repo:repo_name",
                "project:releng:lando:action:tag",
                "project:releng:lando:action:version_bump",
            ],
            id="no_scopes",
        ),
    ),
)
async def test_missing_scopes(aioresponses, github_installation_responses, context, scopes, missing):
    payload = {
        "actions": ["tag", "version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": ["browser/config/version.txt"],
            "next_version": "135.0",
        },
    }

    setup_test(aioresponses, github_installation_responses, context, payload, ["version_bump"])

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised TaskVerificationError"
    except TaskVerificationError as e:
        assert "required scope(s) not present" in e.args[0]
        for m in missing:
            assert m in e.args[0]


@pytest.mark.asyncio
async def test_dontbuild_properly_errors(aioresponses, github_installation_responses, context):
    payload = {"actions": ["tag"], "lando_repo": "repo_name", "tag_info": {"tags": ["FIREFOX_139_0_RELEASE"]}, "dontbuild": True}
    await run_test(
        aioresponses, github_installation_responses, context, payload, ["tag"], err=TaskVerificationError, errmsg="dontbuild is only respected in l10n_bump"
    )


@pytest.mark.asyncio
async def test_ignore_closed_tree_properly_errors(aioresponses, github_installation_responses, context):
    payload = {"actions": ["tag"], "lando_repo": "repo_name", "tag_info": {"tags": ["FIREFOX_139_0_RELEASE"]}, "ignore_closed_tree": True}
    await run_test(
        aioresponses,
        github_installation_responses,
        context,
        payload,
        ["tag"],
        err=TaskVerificationError,
        errmsg="ignore_closed_tree is only respected in l10n_bump and android_l10n_sync",
    )


@pytest.mark.asyncio
async def test_failure_to_submit_to_lando_500(aioresponses, github_installation_responses, context):
    payload = {
        "actions": ["version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": ["browser/config/version.txt"],
            "next_version": "135.0",
        },
    }
    initial_values = {"browser/config/version.txt": "134.0"}
    submit_uri, _, _, scopes = setup_test(aioresponses, github_installation_responses, context, payload, ["version_bump"])
    setup_github_graphql_responses(aioresponses, get_files_payload(initial_values))

    for _ in range(10):
        aioresponses.post(submit_uri, status=500)

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised ClientResponseError"
    except ClientResponseError as e:
        assert e.status == 500


@pytest.mark.asyncio
async def test_to_submit_to_lando_no_status_url(aioresponses, github_installation_responses, context):
    payload = {
        "actions": ["version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": ["browser/config/version.txt"],
            "next_version": "135.0",
        },
    }
    initial_values = {"browser/config/version.txt": "134.0"}
    submit_uri, _, _, scopes = setup_test(aioresponses, github_installation_responses, context, payload, ["version_bump"])
    setup_github_graphql_responses(aioresponses, get_files_payload(initial_values))
    aioresponses.post(submit_uri, status=202, payload={})

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised LandoscriptError"
    except LandoscriptError as e:
        assert "couldn't find status url" in e.args[0]


@pytest.mark.asyncio
async def test_lando_polling_result_not_correct(aioresponses, github_installation_responses, context):
    payload = {
        "actions": ["version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": ["browser/config/version.txt"],
            "next_version": "135.0",
        },
    }
    initial_values = {"browser/config/version.txt": "134.0"}
    submit_uri, status_uri, job_id, scopes = setup_test(aioresponses, github_installation_responses, context, payload, ["version_bump"])
    setup_github_graphql_responses(aioresponses, get_files_payload(initial_values))
    aioresponses.post(submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"})
    aioresponses.get(status_uri, status=200, payload={})

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised LandoscriptError"
    except LandoscriptError as e:
        assert "status is not LANDED" in e.args[0]


@pytest.mark.parametrize("status", ["SUBMITTED", "IN_PROGRESS", "DEFERRED"])
@pytest.mark.asyncio
async def test_lando_200_status_retries(aioresponses, github_installation_responses, context, status):
    payload = {
        "actions": ["version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": ["browser/config/version.txt"],
            "next_version": "135.0",
        },
    }
    initial_values = {"browser/config/version.txt": "134.0"}
    submit_uri, status_uri, job_id, scopes = setup_test(aioresponses, github_installation_responses, context, payload, ["version_bump"])
    setup_github_graphql_responses(aioresponses, get_files_payload(initial_values))
    aioresponses.post(submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"})
    aioresponses.get(
        status_uri,
        status=200,
        payload={
            "commits": ["abcdef123"],
            "push_id": job_id,
            "status": status,
        },
    )
    aioresponses.get(
        status_uri,
        status=200,
        payload={
            "commits": ["abcdef123"],
            "push_id": job_id,
            "status": "LANDED",
        },
    )

    context.task = {"payload": payload, "scopes": scopes}
    await async_main(context)

    assert_status_response(aioresponses.requests, status_uri, attempts=2)


@pytest.mark.asyncio
async def test_lando_polling_retry_on_failure(aioresponses, github_installation_responses, context):
    payload = {
        "actions": ["version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": ["browser/config/version.txt"],
            "next_version": "135.0",
        },
    }
    initial_values = {"browser/config/version.txt": "134.0"}
    submit_uri, status_uri, job_id, scopes = setup_test(aioresponses, github_installation_responses, context, payload, ["version_bump"])
    setup_github_graphql_responses(aioresponses, get_files_payload(initial_values))
    aioresponses.post(submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"})
    aioresponses.get(status_uri, status=500, payload={})
    aioresponses.get(
        status_uri,
        status=200,
        payload={
            "commits": ["abcdef123"],
            "push_id": job_id,
            "status": "LANDED",
        },
    )

    context.task = {"payload": payload, "scopes": scopes}
    await async_main(context)

    assert_status_response(aioresponses.requests, status_uri, attempts=2)
