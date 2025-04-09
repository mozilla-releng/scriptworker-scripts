import pytest
from scriptworker.client import TaskVerificationError

from .conftest import run_test


def assert_tag_response(req, tags):
    assert "json" in req.kwargs
    assert "actions" in req.kwargs["json"]
    tag_actions = [action for action in req.kwargs["json"]["actions"] if action["action"] == "tag"]
    assert len(tag_actions) == len(tags)

    requested_tags = set([action["name"] for action in tag_actions])
    assert requested_tags == set(tags)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tags,dry_run",
    (
        pytest.param(
            ["BUILD1"],
            True,
            id="dry_run",
        ),
        pytest.param(
            ["BUILD1"],
            False,
            id="one_tag",
        ),
        pytest.param(
            ["BUILD1", "RELEASE"],
            False,
            id="multiple_tags",
        ),
    ),
)
async def test_success(aioresponses, github_installation_responses, context, tags, dry_run):
    payload = {
        "actions": ["tag"],
        "lando_repo": "repo_name",
        "tags": tags,
        "dry_run": dry_run,
    }

    def assert_func(req):
        assert_tag_response(req, tags)

    await run_test(aioresponses, github_installation_responses, context, payload, ["tag"], not dry_run, assert_func)


@pytest.mark.asyncio
async def test_no_tags(aioresponses, github_installation_responses, context):
    payload = {
        "actions": ["tag"],
        "lando_repo": "repo_name",
        "tags": [],
    }
    await run_test(aioresponses, github_installation_responses, context, payload, ["tag"], err=TaskVerificationError, errmsg="must provide at least one tag!")
