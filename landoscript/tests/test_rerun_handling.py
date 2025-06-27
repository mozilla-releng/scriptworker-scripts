import pytest
from yarl import URL

from landoscript.errors import LandoscriptError
from landoscript.script import async_main
from tests.conftest import assert_status_response, assert_tag_response, run_test, setup_test


@pytest.mark.asyncio
async def test_rerun_previous_lando_job_not_found(monkeypatch, aioresponses, responses, github_installation_responses, context):
    """A rerun that did not find a lando job url from a previous run should
    function as if no lando job was submitted."""
    monkeypatch.setenv("TASKCLUSTER_ROOT_URL", "https://tc")
    monkeypatch.setenv("TASK_ID", "task_id")
    monkeypatch.setenv("RUN_ID", "4")
    tag_info = {
        "revision": "abcdef123456",
        "hg_repo_url": "https://hg.testing/repo",
        "tags": ["BUILD1", "RELEASE"],
    }
    payload = {
        "actions": ["tag"],
        "lando_repo": "repo_name",
        "tag_info": tag_info,
    }
    git_commit = "ghijkl654321"
    aioresponses.get(
        f"{tag_info['hg_repo_url']}/json-rev/{tag_info['revision']}",
        status=200,
        payload={"git_commit": git_commit},
    )

    # previous run status
    task_status_url = "https://tc/api/queue/v1/task/task_id/status"
    task_status_resp = responses.get(
        task_status_url,
        status=200,
        json={
            "status": {
                "runs": [
                    {
                        "runId": 0,
                        "state": "exception",
                    },
                    {
                        "runId": 1,
                        "state": "exception",
                    },
                    {
                        "runId": 2,
                        "state": "exception",
                    },
                    {
                        "runId": 3,
                        "state": "exception",
                    },
                ]
            },
        },
    )
    artifact_info_resps = []
    for i in range(4):
        artifact_url = f"https://tc/api/queue/v1/task/task_id/runs/{i}/artifacts/public%2Fbuild%2Flando-status.txt"
        artifact_info_resps.append(
            responses.get(
                artifact_url,
                status=404,
            )
        )

    def assert_func(req):
        assert_tag_response(req, tag_info, git_commit)
        assert task_status_resp.call_count == 1
        for resp in artifact_info_resps:
            assert resp.call_count == 1

    await run_test(aioresponses, github_installation_responses, context, payload, ["tag"], assert_func=assert_func)


@pytest.mark.asyncio
async def test_rerun_previous_lando_job_succeeded(monkeypatch, aioresponses, responses, github_installation_responses, context):
    """A rerun that finds a lando job that succeeded should return success
    and do nothing else."""
    monkeypatch.setenv("TASKCLUSTER_ROOT_URL", "https://tc")
    monkeypatch.setenv("TASK_ID", "task_id")
    monkeypatch.setenv("RUN_ID", "1")
    tag_info = {
        "revision": "abcdef123456",
        "hg_repo_url": "https://hg.testing/repo",
        "tags": ["BUILD1", "RELEASE"],
    }
    payload = {
        "actions": ["tag"],
        "lando_repo": "repo_name",
        "tag_info": tag_info,
    }
    submit_uri, status_uri, job_id, scopes = setup_test(aioresponses, github_installation_responses, context, payload, ["tag"], "repo_name")
    context.task = {"payload": payload, "scopes": scopes}

    # previous run status
    task_status_url = "https://tc/api/queue/v1/task/task_id/status"
    task_status_resp = responses.get(
        task_status_url,
        status=200,
        json={
            "status": {
                "runs": [
                    {
                        "runId": 0,
                        "state": "completed",
                    },
                ]
            },
        },
    )

    # previous run's status artifact info
    artifact_url = f"https://tc/api/queue/v1/task/task_id/runs/0/artifacts/public%2Fbuild%2Flando-status.txt"
    artifact_info_resp = responses.get(artifact_url, status=303, json={"storageType": "s3", "url": "https://s3.fake/artifact"})

    # the actual artifact
    aioresponses.get(
        "https://s3.fake/artifact",
        status=200,
        body=str(status_uri),
    )

    # response from lando when this run checks on the job
    aioresponses.get(
        status_uri,
        status=200,
        payload={
            "commits": ["abcdef123"],
            "push_id": job_id,
            "status": "LANDED",
        },
    )

    await async_main(context)

    assert_status_response(aioresponses.requests, status_uri)
    assert task_status_resp.call_count == 1
    # ensure we found the previous run's artifact
    assert artifact_info_resp.call_count == 1
    assert ("GET", URL("https://s3.fake/artifact")) in aioresponses.requests
    # ensure another lando job was _not_ submitted
    assert ("POST", submit_uri) not in aioresponses.requests


@pytest.mark.asyncio
async def test_rerun_previous_lando_job_failed(monkeypatch, aioresponses, responses, github_installation_responses, context):
    """A rerun that finds a lando job that succeeded should return failure
    and do nothing else."""
    monkeypatch.setenv("TASKCLUSTER_ROOT_URL", "https://tc")
    monkeypatch.setenv("TASK_ID", "task_id")
    monkeypatch.setenv("RUN_ID", "1")
    tag_info = {
        "revision": "abcdef123456",
        "hg_repo_url": "https://hg.testing/repo",
        "tags": ["BUILD1", "RELEASE"],
    }
    payload = {
        "actions": ["tag"],
        "lando_repo": "repo_name",
        "tag_info": tag_info,
    }
    submit_uri, status_uri, job_id, scopes = setup_test(aioresponses, github_installation_responses, context, payload, ["tag"], "repo_name")
    context.task = {"payload": payload, "scopes": scopes}

    # previous run status
    task_status_url = "https://tc/api/queue/v1/task/task_id/status"
    task_status_resp = responses.get(
        task_status_url,
        status=200,
        json={
            "status": {
                "runs": [
                    {
                        "runId": 0,
                        "state": "exception",
                    },
                ]
            },
        },
    )

    # previous run's status artifact
    artifact_url = f"https://tc/api/queue/v1/task/task_id/runs/0/artifacts/public%2Fbuild%2Flando-status.txt"
    artifact_info_resp = responses.get(artifact_url, status=303, json={"storageType": "s3", "url": "https://s3.fake/artifact"})

    # the actual artifact
    aioresponses.get(
        "https://s3.fake/artifact",
        status=200,
        body=str(status_uri),
    )

    # response from lando when this run checks on the job
    aioresponses.get(
        status_uri,
        status=200,
        payload={
            "commits": ["abcdef123"],
            "push_id": job_id,
            "status": "FAILED",
        },
    )

    try:
        await async_main(context)
        assert False, f"should've raised LandoScriptError"
    except LandoscriptError as e:
        assert_status_response(aioresponses.requests, status_uri)

        assert task_status_resp.call_count == 1
        # ensure we got the correct error
        assert "Landing status is FAILED" in e.args[0]
        # ensure we found the previous run's artifact
        assert artifact_info_resp.call_count == 1
        assert ("GET", URL("https://s3.fake/artifact")) in aioresponses.requests
        # ensure another lando job was _not_ submitted
        assert ("POST", submit_uri) not in aioresponses.requests


@pytest.mark.asyncio
async def test_rerun_previous_lando_job_in_progress(monkeypatch, aioresponses, responses, github_installation_responses, context):
    """A rerun that finds a lando job still in progress should poll that job
    for status and do nothing else."""
    monkeypatch.setenv("TASKCLUSTER_ROOT_URL", "https://tc")
    monkeypatch.setenv("TASK_ID", "task_id")
    monkeypatch.setenv("RUN_ID", "1")
    tag_info = {
        "revision": "abcdef123456",
        "hg_repo_url": "https://hg.testing/repo",
        "tags": ["BUILD1", "RELEASE"],
    }
    payload = {
        "actions": ["tag"],
        "lando_repo": "repo_name",
        "tag_info": tag_info,
    }
    submit_uri, status_uri, job_id, scopes = setup_test(aioresponses, github_installation_responses, context, payload, ["tag"], "repo_name")
    context.task = {"payload": payload, "scopes": scopes}

    # previous run status
    task_status_url = "https://tc/api/queue/v1/task/task_id/status"
    task_status_resp = responses.get(
        task_status_url,
        status=200,
        json={
            "status": {
                "runs": [
                    {
                        "runId": 0,
                        "state": "completed",
                    },
                ]
            },
        },
    )

    # previous run's status artifact
    artifact_url = f"https://tc/api/queue/v1/task/task_id/runs/0/artifacts/public%2Fbuild%2Flando-status.txt"
    artifact_info_resp = responses.get(artifact_url, status=303, json={"storageType": "s3", "url": "https://s3.fake/artifact"})

    # the actual artifact
    aioresponses.get(
        "https://s3.fake/artifact",
        status=200,
        body=str(status_uri),
    )

    # response from lando when this run checks on the job
    aioresponses.get(
        status_uri,
        status=200,
        payload={
            "commits": ["abcdef123"],
            "push_id": job_id,
            "status": "IN_PROGRESS",
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

    await async_main(context)

    assert_status_response(aioresponses.requests, status_uri, 2)
    assert task_status_resp.call_count == 1
    # ensure we found the previous run's artifact
    assert artifact_info_resp.call_count == 1
    assert ("GET", URL("https://s3.fake/artifact")) in aioresponses.requests
    # ensure another lando job was _not_ submitted
    assert ("POST", submit_uri) not in aioresponses.requests


@pytest.mark.asyncio
async def test_rerun_previous_run_failed(monkeypatch, aioresponses, responses, github_installation_responses, context):
    """A rerun that finds the previous run has failed should not try to
    re-return the previous lando status, if it existed; it should run the
    job as usual. This ensures that reruns for, eg: problems on the Lando
    server behave as expected."""
    monkeypatch.setenv("TASKCLUSTER_ROOT_URL", "https://tc")
    monkeypatch.setenv("TASK_ID", "task_id")
    monkeypatch.setenv("RUN_ID", "1")
    tag_info = {
        "revision": "abcdef123456",
        "hg_repo_url": "https://hg.testing/repo",
        "tags": ["BUILD1", "RELEASE"],
    }
    payload = {
        "actions": ["tag"],
        "lando_repo": "repo_name",
        "tag_info": tag_info,
    }

    # previous run status
    task_status_url = "https://tc/api/queue/v1/task/task_id/status"
    task_status_resp = responses.get(
        task_status_url,
        status=200,
        json={
            "status": {
                "runs": [
                    {
                        "runId": 0,
                        "state": "failed",
                    },
                ]
            },
        },
    )

    git_commit = "ghijkl654321"
    aioresponses.get(
        f"{tag_info['hg_repo_url']}/json-rev/{tag_info['revision']}",
        status=200,
        payload={"git_commit": git_commit},
    )

    def assert_func(req):
        assert_tag_response(req, tag_info, git_commit)
        assert task_status_resp.call_count == 1

    await run_test(aioresponses, github_installation_responses, context, payload, ["tag"], True, assert_func)
