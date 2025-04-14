import pytest
from scriptworker.client import TaskVerificationError
from simple_github.client import GITHUB_GRAPHQL_ENDPOINT

from landoscript.errors import LandoscriptError
from landoscript.script import async_main
from landoscript.actions.version_bump import ALLOWED_BUMP_FILES
from landoscript.util.version import _VERSION_CLASS_PER_BEGINNING_OF_PATH

from .conftest import (
    assert_lando_submission_response,
    assert_status_response,
    fetch_files_payload,
    run_test,
    setup_github_graphql_responses,
    setup_test,
    assert_add_commit_response,
)


def assert_success(req, commit_msg_strings, initial_values, expected_bumps):
    assert "json" in req.kwargs
    assert "actions" in req.kwargs["json"]
    create_commit_actions = [action for action in req.kwargs["json"]["actions"] if action["action"] == "create-commit"]
    assert len(create_commit_actions) == 1
    action = create_commit_actions[0]

    assert_add_commit_response(action, commit_msg_strings, initial_values, expected_bumps)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,initial_values,expected_bumps,commit_msg_strings",
    (
        pytest.param(
            {
                "actions": ["version_bump"],
                "lando_repo": "repo_name",
                "dry_run": True,
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
            ["Automatic version bump", "NO BUG", "a=release", "CLOSED TREE", "DONTBUILD"],
            id="dryrun",
        ),
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
            ["Automatic version bump", "NO BUG", "a=release", "CLOSED TREE", "DONTBUILD"],
            id="one_file_new_version",
        ),
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
                "browser/config/version.txt": "134.0\n",
            },
            {
                "browser/config/version.txt": "135.0\n",
            },
            ["Automatic version bump", "NO BUG", "a=release", "CLOSED TREE", "DONTBUILD"],
            id="one_file_new_version_retains_newline",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "lando_repo": "repo_name",
                "version_bump_info": {
                    "files": ["browser/config/version.txt"],
                    "next_version": "134.0.1",
                },
            },
            {
                "browser/config/version.txt": "134.0",
            },
            {
                "browser/config/version.txt": "134.0.1",
            },
            ["Automatic version bump", "NO BUG", "a=release", "CLOSED TREE", "DONTBUILD"],
            id="one_file_minor_bump",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "lando_repo": "repo_name",
                "version_bump_info": {
                    "files": ["browser/config/version.txt"],
                    "next_version": "134.0b3",
                },
            },
            {
                "browser/config/version.txt": "134.0b2",
            },
            {
                "browser/config/version.txt": "134.0b3",
            },
            ["Automatic version bump", "NO BUG", "a=release", "CLOSED TREE", "DONTBUILD"],
            id="beta_bump_display",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "lando_repo": "repo_name",
                "version_bump_info": {
                    "files": ["browser/config/version.txt"],
                    "next_version": "128.2.1esr",
                },
            },
            {
                "browser/config/version.txt": "128.2.0",
            },
            {
                "browser/config/version.txt": "128.2.1",
            },
            ["Automatic version bump", "NO BUG", "a=release", "CLOSED TREE", "DONTBUILD"],
            id="esr_bump",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "lando_repo": "repo_name",
                "version_bump_info": {
                    "files": ["browser/config/version_display.txt"],
                    "next_version": "128.2.1esr",
                },
            },
            {
                "browser/config/version_display.txt": "128.2.0esr",
            },
            {
                "browser/config/version_display.txt": "128.2.1esr",
            },
            ["Automatic version bump", "NO BUG", "a=release", "CLOSED TREE", "DONTBUILD"],
            id="esr_bump_display",
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
            ["Automatic version bump", "NO BUG", "a=release", "CLOSED TREE", "DONTBUILD"],
            id="many_files_all_changed",
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
                    "next_version": "135.0b3",
                },
            },
            {
                "browser/config/version.txt": "135.0",
                "browser/config/version_display.txt": "135.0b2",
                "config/milestone.txt": "135.0",
                "mobile/android/version.txt": "135.0b2",
            },
            {
                "browser/config/version_display.txt": "135.0b3",
                "mobile/android/version.txt": "135.0b3",
            },
            ["Automatic version bump", "NO BUG", "a=release", "CLOSED TREE", "DONTBUILD"],
            id="many_files_some_changed",
        ),
    ),
)
async def test_success_with_bumps(aioresponses, github_installation_responses, context, payload, initial_values, expected_bumps, commit_msg_strings):
    setup_github_graphql_responses(aioresponses, fetch_files_payload(initial_values))
    dryrun = payload.get("dry_run", False)

    def assert_func(req):
        assert_success(req, commit_msg_strings, initial_values, expected_bumps)

    await run_test(aioresponses, github_installation_responses, context, payload, ["version_bump"], not dryrun, assert_func)


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
    setup_github_graphql_responses(aioresponses, fetch_files_payload(initial_values))

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
    assert_success(req, commit_msg_strings, initial_values, expected_bumps)
    assert_status_response(aioresponses.requests, status_uri, attempts=2)
    assert (context.config["artifact_dir"] / "public/build/version-bump.diff").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,initial_values",
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
                "browser/config/version.txt": "135.0",
            },
            id="one_file_no_change",
        ),
    ),
)
async def test_success_without_bumps(aioresponses, github_installation_responses, context, payload, initial_values):
    submit_uri, status_uri, _, scopes = setup_test(github_installation_responses, context, payload, ["version_bump"])
    setup_github_graphql_responses(aioresponses, fetch_files_payload(initial_values))

    context.task = {"payload": payload, "scopes": scopes}
    await async_main(context)

    assert ("POST", submit_uri) not in aioresponses.requests
    assert ("GET", status_uri) not in aioresponses.requests


@pytest.mark.asyncio
async def test_failure_to_fetch_files(aioresponses, github_installation_responses, context):
    payload = {
        "actions": ["version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": ["browser/config/version.txt"],
            "next_version": "135.0",
        },
    }
    _, _, _, scopes = setup_test(github_installation_responses, context, payload, ["version_bump"])

    # 5 attempts is hardcoded deeper than we can reasonable override it; so
    # just expect it
    for _ in range(5):
        aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=500)

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised LandoscriptError"
    except LandoscriptError as e:
        assert "couldn't retrieve bump files from github" in e.args[0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "files,first_bad_file",
    (
        pytest.param(
            ["browser/config/unknown.txt"],
            "browser/config/unknown.txt",
            id="one_file",
        ),
        pytest.param(
            ["browser/config/version.txt", "browser/config/unknown.txt", "foo/bar/baz"],
            "browser/config/unknown.txt",
            id="many_files",
        ),
    ),
)
async def test_bad_bumpfile(aioresponses, github_installation_responses, context, files, first_bad_file):
    payload = {
        "actions": ["version_bump"],
        "lando_repo": "repo_name",
        "version_bump_info": {
            "files": files,
            "next_version": "135.0",
        },
    }
    await run_test(
        aioresponses,
        github_installation_responses,
        context,
        payload,
        ["version_bump"],
        err=TaskVerificationError,
        errmsg=f"{first_bad_file} is not in version bump allowlist",
    )


def test_no_overlaps_in_version_classes():
    for prefix1 in _VERSION_CLASS_PER_BEGINNING_OF_PATH:
        for prefix2 in _VERSION_CLASS_PER_BEGINNING_OF_PATH:
            if prefix1 == prefix2:
                continue
            assert not prefix2.startswith(prefix1)


def test_all_bump_files_have_version_class():
    for bump_file in ALLOWED_BUMP_FILES:
        assert any([bump_file.startswith(path) for path in _VERSION_CLASS_PER_BEGINNING_OF_PATH])
