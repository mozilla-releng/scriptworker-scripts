from landoscript.errors import LandoscriptError
import pytest
from scriptworker.client import TaskVerificationError

from .conftest import run_test


def assert_tag_response(req, tag_info, target_revision):
    assert "json" in req.kwargs
    assert "actions" in req.kwargs["json"]
    tag_actions = [action for action in req.kwargs["json"]["actions"] if action["action"] == "tag"]
    assert len(tag_actions) == len(tag_info["tags"])

    requested_tags = set([action["name"] for action in tag_actions])
    assert requested_tags == set(tag_info["tags"])

    revisions = set([action["target"] for action in tag_actions])
    assert len(revisions) == 1
    assert revisions.pop() == target_revision


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tag_info,dry_run",
    (
        pytest.param(
            {
                "revision": "abcdef123456",
                "hg_repo_url": "https://hg.testing/repo",
                "tags": ["BUILD1"],
            },
            True,
            id="dry_run",
        ),
        pytest.param(
            {
                "revision": "abcdef123456",
                "hg_repo_url": "https://hg.testing/repo",
                "tags": ["BUILD1"],
            },
            False,
            id="one_tag",
        ),
        pytest.param(
            {
                "revision": "abcdef123456",
                "hg_repo_url": "https://hg.testing/repo",
                "tags": ["BUILD1", "RELEASE"],
            },
            False,
            id="multiple_tags",
        ),
    ),
)
async def test_success(aioresponses, github_installation_responses, context, tag_info, dry_run):
    payload = {
        "actions": ["tag"],
        "lando_repo": "repo_name",
        "tag_info": tag_info,
        "dry_run": dry_run,
    }
    git_commit = "ghijkl654321"
    aioresponses.get(
        f"{tag_info['hg_repo_url']}/json-rev/{tag_info['revision']}",
        status=200,
        payload={"git_commit": git_commit},
    )

    def assert_func(req):
        assert_tag_response(req, tag_info, git_commit)

    await run_test(aioresponses, github_installation_responses, context, payload, ["tag"], not dry_run, assert_func)


@pytest.mark.asyncio
async def test_no_tags(aioresponses, github_installation_responses, context):
    payload = {
        "actions": ["tag"],
        "lando_repo": "repo_name",
        "tag_info": {
            "revision": "abcdef123456",
            "hg_repo_url": "https://hg.testing/repo",
            "tags": [],
        },
    }
    await run_test(aioresponses, github_installation_responses, context, payload, ["tag"], err=TaskVerificationError, errmsg="must provide at least one tag!")


@pytest.mark.asyncio
async def test_hg_repo_url(aioresponses, github_installation_responses, context):
    payload = {
        "actions": ["tag"],
        "lando_repo": "repo_name",
        "tag_info": {
            "revision": "abcdef123456",
            "tags": ["FOO"],
        },
    }
    await run_test(aioresponses, github_installation_responses, context, payload, ["tag"], err=TaskVerificationError, errmsg="must provide hg_repo_url!")


@pytest.mark.parametrize(
    "hg_response",
    (
        pytest.param(
            {},
            id="no_git_commit",
        ),
        pytest.param(
            {"git_commit": None},
            id="git_commit_is_none",
        ),
    ),
)
@pytest.mark.asyncio
async def test_no_git_commit(aioresponses, github_installation_responses, context, hg_response):
    payload = {
        "actions": ["tag"],
        "lando_repo": "repo_name",
        "tag_info": {
            "revision": "abcdef123456",
            "hg_repo_url": "https://hg.testing/repo",
            "tags": ["FOO"],
        },
    }

    aioresponses.get(
        f"https://hg.testing/repo/json-rev/abcdef123456",
        status=200,
        payload=hg_response,
    )

    await run_test(
        aioresponses, github_installation_responses, context, payload, ["tag"], err=LandoscriptError, errmsg="Couldn't look up target revision for tag(s) in hg"
    )
