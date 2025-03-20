import pytest
from scriptworker.client import TaskVerificationError
from yarl import URL

from landoscript.script import async_main


def assert_tag_response(requests, submit_uri, tags, attempts=1):
    # make sure that exactly one request was made
    # (a single request can add more than one commit, so there should never
    # be a need for more than 1 request)
    assert ("POST", submit_uri) in requests
    reqs = requests[("POST", submit_uri)]
    assert len(reqs) == attempts

    # there might be more than one in cases where we retry; we assume that
    # the requests are the same for all attempts
    req = reqs[0]
    assert "json" in req.kwargs
    assert "actions" in req.kwargs["json"]
    assert len(req.kwargs["json"]["actions"]) == len(tags)

    requested_tags = set([action["name"] for action in req.kwargs["json"]["actions"]])
    assert requested_tags == set(tags)


def assert_status_response(requests, status_uri, attempts=1):
    assert ("GET", status_uri) in requests
    reqs = requests[("GET", status_uri)]
    # there might be more than one in cases where we retry; we assume that
    # the requests are the same for all attempts
    assert len(reqs) == attempts


def setup_test(github_installation_responses, context, payload, repo="repo_name"):
    lando_repo = payload["lando_repo"]
    lando_api = context.config["lando_api"]
    owner = context.config["lando_name_to_github_repo"][lando_repo]["owner"]
    submit_uri = URL(f"{lando_api}/api/v1/{lando_repo}")
    job_id = 12345
    status_uri = URL(f"{lando_api}/push/{job_id}")

    github_installation_responses(owner)

    scopes = [
        f"project:releng:lando:repo:{repo}",
        f"project:releng:lando:action:tag",
    ]

    return submit_uri, status_uri, job_id, scopes


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
    submit_uri, status_uri, job_id, scopes = setup_test(github_installation_responses, context, payload)

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
        assert_tag_response(aioresponses.requests, submit_uri, tags)
        assert_status_response(aioresponses.requests, status_uri)


@pytest.mark.asyncio
async def test_no_tags(github_installation_responses, context):
    payload = {
        "actions": ["tag"],
        "lando_repo": "repo_name",
        "tags": [],
    }
    _, _, _, scopes = setup_test(github_installation_responses, context, payload)

    context.task = {"payload": payload, "scopes": scopes}

    try:
        await async_main(context)
        assert False, "should've raised TaskVerificationError"
    except TaskVerificationError as e:
        assert "must provide at least one tag!" in e.args[0]


@pytest.mark.asyncio
async def test_missing_scopes(context):
    payload = {
        "actions": ["tag"],
        "lando_repo": "repo_name",
        "tags": ["BUILD1"],
    }

    context.task = {"payload": payload, "scopes": ["project:releng:lando:repo:repo_name"]}

    try:
        await async_main(context)
        assert False, "should've raised TaskVerificationError"
    except TaskVerificationError as e:
        assert "required scope(s) not present" in e.args[0]
        assert "project:releng:lando:action:tag" in e.args[0]
