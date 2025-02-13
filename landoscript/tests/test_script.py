import os.path
from landoscript.types import Payload
import pytest
import tempfile

from landoscript.script import async_main
from landoscript.types import Context
from simple_github.client import GITHUB_API_ENDPOINT, GITHUB_GRAPHQL_ENDPOINT
from yarl import URL


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,initial_values,expected_bumps,commit_msg_strings",
    (
        pytest.param(
            {
                "actions": ["version_bump"],
                "source_repo": "https://github.com/fake/fake_repo",
                "branch": "fake_branch",
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
            id="one_file_new_version",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "source_repo": "https://github.com/fake/fake_repo",
                "branch": "fake_branch",
                "version_bump_info": {
                    "files": ["browser/config/version.txt"],
                    "next_version": "135.0",
                },
            },
            {
                "browser/config/version.txt": "135.0",
            },
            {},
            [],
            id="one_file_no_change",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "source_repo": "https://github.com/fake/fake_repo",
                "branch": "fake_branch",
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
            ["Automatic version bump", "NO BUG", "a=release"],
            id="one_file_minor_bump",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "source_repo": "https://github.com/fake/fake_repo",
                "branch": "fake_branch",
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
            ["Automatic version bump", "NO BUG", "a=release"],
            id="beta_bump_display",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "source_repo": "https://github.com/fake/fake_repo",
                "branch": "fake_branch",
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
            ["Automatic version bump", "NO BUG", "a=release"],
            id="esr_bump",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "source_repo": "https://github.com/fake/fake_repo",
                "branch": "fake_branch",
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
            ["Automatic version bump", "NO BUG", "a=release"],
            id="esr_bump_display",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "source_repo": "https://github.com/fake/fake_repo",
                "branch": "fake_branch",
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
            id="many_files_all_changed",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "source_repo": "https://github.com/fake/fake_repo",
                "branch": "fake_branch",
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
            ["Automatic version bump", "NO BUG", "a=release"],
            id="many_files_some_changed",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "source_repo": "https://github.com/fake/fake_repo",
                "branch": "fake_branch",
                "version_bump_info": {
                    "files": ["browser/config/version.txt"],
                    "next_version": "135.0",
                },
                "dontbuild": True,
            },
            {
                "browser/config/version.txt": "134.0",
            },
            {
                "browser/config/version.txt": "135.0",
            },
            ["Automatic version bump", "NO BUG", "a=release", "DONTBUILD"],
            id="dontbuild_includes_correct_commit_message",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "source_repo": "https://github.com/fake/fake_repo",
                "branch": "fake_branch",
                "version_bump_info": {
                    "files": ["browser/config/version.txt"],
                    "next_version": "135.0",
                },
                "ignore_closed_true": True,
            },
            {
                "browser/config/version.txt": "134.0",
            },
            {
                "browser/config/version.txt": "135.0",
            },
            ["Automatic version bump", "NO BUG", "a=release", "CLOSED TREE"],
            id="closed_tree_includes_correct_commit_message",
        ),
        pytest.param(
            {
                "actions": ["version_bump"],
                "source_repo": "https://github.com/fake/fake_repo",
                "branch": "fake_branch",
                "version_bump_info": {
                    "files": ["browser/config/version.txt"],
                    "next_version": "135.0",
                },
                "dontbuild": True,
                "ignore_closed_true": True,
            },
            {
                "browser/config/version.txt": "134.0",
            },
            {
                "browser/config/version.txt": "135.0",
            },
            ["Automatic version bump", "NO BUG", "a=release", "DONTBUILD", "CLOSED TREE"],
            id="dont_build_and_closed_tree",
        ),
    ),
)
async def test_version_bump(aioresponses, context: Context, payload: Payload, initial_values, expected_bumps, commit_msg_strings):
    config = context.config
    source_repo = payload["source_repo"]
    # TODO: maybe this belongs in a parameter?
    repo_name = source_repo.split("/")[-1]
    owner = source_repo.split("/")[-2]
    branch = payload["branch"]
    uri = URL(f"{config['lando_api']}/api/v1/{repo_name}/{branch}")

    aioresponses.post(uri, payload={"foo": "bar"})

    aioresponses.get(
        f"{GITHUB_API_ENDPOINT}/app/installations",
        status=200,
        payload=[{"id": 1, "account": {"login": owner}}],
    )
    aioresponses.post(
        f"{GITHUB_API_ENDPOINT}/app/installations/1/access_tokens",
        status=200,
        payload={"token": "111"},
    )

    github_response = {}
    for file, contents in initial_values.items():
        github_response[file] = f"{contents}\n"

    aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=200, payload={"data": {"repository": {k: {"text": v} for k, v in github_response.items()}}})

    context.task = {"payload": payload}
    await async_main(context)

    if not expected_bumps:
        assert ("POST", uri) not in aioresponses.requests
        return

    assert ("POST", uri) in aioresponses.requests
    reqs = aioresponses.requests[("POST", uri)]
    assert len(reqs) == 1
    req = reqs[0]
    assert "json" in req.kwargs
    assert "actions" in req.kwargs["json"]
    assert len(req.kwargs["json"]["actions"]) == 1
    action = req.kwargs["json"]["actions"][0]
    assert action["action"] == "add-commit"

    for msg in commit_msg_strings:
        assert msg in action["content"]

    diffs = action["content"].split("\ndiff")
    for file, after in expected_bumps.items():
        for diff in diffs:
            before = initial_values[file]
            if file in diff and f"-{before}\n+{after}\n" in diff:
                break
        else:
            assert False, f"no version bump found for {file}: {diffs}"

# tsets for each action on their own
# tests for combinations of actions
# tests for failures
