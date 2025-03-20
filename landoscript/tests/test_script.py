from aiohttp import ClientResponseError
import pytest
from scriptworker.client import TaskVerificationError

from landoscript.errors import LandoscriptError
from landoscript.script import async_main
from .conftest import assert_lando_submission_response, assert_status_response, setup_test
from .test_tag import assert_tag_response
from .test_version_bump import assert_add_commit_response, setup_fetch_files_response


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,initial_values,expected_bumps,commit_msg_strings,tags,dry_run",
    (
        pytest.param(
            {
                "actions": ["tag", "version_bump"],
                "lando_repo": "repo_name",
                "version_bump_info": {
                    "files": ["browser/config/version.txt"],
                    "next_version": "135.0",
                },
                "tags": ["RELEASE"],
                "dry_run": True,
            },
            {
                "browser/config/version.txt": "134.0",
            },
            {
                "browser/config/version.txt": "135.0",
            },
            ["Automatic version bump", "NO BUG", "a=release"],
            ["RELEASE"],
            True,
            id="tag_and_bump",
        ),
        pytest.param(
            {
                "actions": ["tag", "version_bump"],
                "lando_repo": "repo_name",
                "version_bump_info": {
                    "files": ["browser/config/version.txt"],
                    "next_version": "135.0",
                },
                "tags": ["RELEASE"],
            },
            {
                "browser/config/version.txt": "134.0",
            },
            {
                "browser/config/version.txt": "135.0",
            },
            ["Automatic version bump", "NO BUG", "a=release"],
            ["RELEASE"],
            False,
            id="tag_and_bump",
        ),
    ),
)
async def test_tag_and_bump(aioresponses, github_installation_responses, context, payload, dry_run, initial_values, expected_bumps, commit_msg_strings, tags):
    submit_uri, status_uri, job_id, scopes = setup_test(github_installation_responses, context, payload, payload["actions"])
    setup_fetch_files_response(aioresponses, 200, initial_values)

    if not dry_run:
        aioresponses.post(
            submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"}
        )

        aioresponses.get(
            status_uri,
            status=200,
            payload={
                "commits": ["abcdef123"],
                "push_id": job_id,
                "status": "completed",
            },
        )

    context.task = {"payload": payload, "scopes": scopes}
    await async_main(context)

    assert (context.config["artifact_dir"] / "public/build/version-bump.diff").exists()
    if not dry_run:
        req = assert_lando_submission_response(aioresponses.requests, submit_uri)
        assert_add_commit_response(req, commit_msg_strings, initial_values, expected_bumps)
        assert_status_response(aioresponses.requests, status_uri)
        assert_tag_response(req, tags)


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
    submit_uri, status_uri, job_id, scopes = setup_test(github_installation_responses, context, payload, ["version_bump"])
    setup_fetch_files_response(aioresponses, 200, initial_values)

    aioresponses.post(submit_uri, status=500)
    aioresponses.post(submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"})

    aioresponses.get(status_uri, status=202, payload={"status": "pending", "job_id": job_id, "message": "foo", "started_at": "2025-03-08T12:25:00Z"})
    aioresponses.get(
        status_uri,
        status=200,
        payload={
            "commits": ["abcdef123"],
            "push_id": job_id,
            "status": "completed",
        },
    )

    context.task = {"payload": payload, "scopes": scopes}
    await async_main(context)

    req = assert_lando_submission_response(aioresponses.requests, submit_uri, attempts=2)
    assert_add_commit_response(req, commit_msg_strings, initial_values, expected_bumps)
    assert_status_response(aioresponses.requests, status_uri, attempts=2)
    assert (context.config["artifact_dir"] / "public/build/version-bump.diff").exists()


@pytest.mark.asyncio
async def test_no_actions(github_installation_responses, context):
    payload = {
        "actions": [],
        "lando_repo": "repo_name",
    }
    _, _, _, scopes = setup_test(github_installation_responses, context, payload, [])

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised TaskVerificationError"
    except TaskVerificationError as e:
        assert "must provide at least one action!" in e.args[0]


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
async def test_missing_scopes(context, scopes, missing):
    payload = {
        "actions": ["tag", "version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": ["browser/config/version.txt"],
            "next_version": "135.0",
        },
    }

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised TaskVerificationError"
    except TaskVerificationError as e:
        assert "required scope(s) not present" in e.args[0]
        for m in missing:
            assert m in e.args[0]


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
    submit_uri, _, _, scopes = setup_test(github_installation_responses, context, payload, ["version_bump"])
    setup_fetch_files_response(aioresponses, 200, initial_values)

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
    submit_uri, _, _, scopes = setup_test(github_installation_responses, context, payload, ["version_bump"])
    setup_fetch_files_response(aioresponses, 200, initial_values)
    aioresponses.post(submit_uri, status=202, payload={})

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised LandoscriptError"
    except LandoscriptError as e:
        assert "couldn't find status url" in e.args[0]


@pytest.mark.asyncio
async def test_lando_polling_result_not_completed(aioresponses, github_installation_responses, context):
    payload = {
        "actions": ["version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": ["browser/config/version.txt"],
            "next_version": "135.0",
        },
    }
    initial_values = {"browser/config/version.txt": "134.0"}
    submit_uri, status_uri, job_id, scopes = setup_test(github_installation_responses, context, payload, ["version_bump"])
    setup_fetch_files_response(aioresponses, 200, initial_values)
    aioresponses.post(submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"})
    aioresponses.get(status_uri, status=200, payload={})

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised LandoscriptError"
    except LandoscriptError as e:
        assert "status is not completed" in e.args[0]


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
    submit_uri, status_uri, job_id, scopes = setup_test(github_installation_responses, context, payload, ["version_bump"])
    setup_fetch_files_response(aioresponses, 200, initial_values)
    aioresponses.post(submit_uri, status=202, payload={"job_id": job_id, "status_url": str(status_uri), "message": "foo", "started_at": "2025-03-08T12:25:00Z"})
    aioresponses.get(status_uri, status=500, payload={})
    aioresponses.get(
        status_uri,
        status=200,
        payload={
            "commits": ["abcdef123"],
            "push_id": job_id,
            "status": "completed",
        },
    )

    context.task = {"payload": payload, "scopes": scopes}
    await async_main(context)

    assert_status_response(aioresponses.requests, status_uri, attempts=2)
