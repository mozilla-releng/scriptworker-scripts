import pytest
from scriptworker.client import TaskVerificationError

from landoscript.script import async_main

from .conftest import assert_lando_submission_response, assert_status_response, setup_test


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
    submit_uri, status_uri, job_id, scopes = setup_test(github_installation_responses, context, payload, ["tag"])

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

    if not dry_run:
        req = assert_lando_submission_response(aioresponses.requests, submit_uri)
        assert_tag_response(req, tags)
        assert_status_response(aioresponses.requests, status_uri)


@pytest.mark.asyncio
async def test_no_tags(github_installation_responses, context):
    payload = {
        "actions": ["tag"],
        "lando_repo": "repo_name",
        "tags": [],
    }
    _, _, _, scopes = setup_test(github_installation_responses, context, payload, ["tag"])

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised TaskVerificationError"
    except TaskVerificationError as e:
        assert "must provide at least one tag!" in e.args[0]
