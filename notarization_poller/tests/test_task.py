#!/usr/bin/env python
# coding=utf-8
"""Test notarization_poller.task
"""
import asyncio
import logging
from contextlib import asynccontextmanager

import aiohttp
import arrow
import pytest
from scriptworker_client.constants import STATUSES
from scriptworker_client.exceptions import Download404, DownloadError, TaskError
from taskcluster.exceptions import TaskclusterRestFailure

import notarization_poller.task as nptask
from notarization_poller.exceptions import RetryError

from . import noop_async


# Constants, fixtures, and helpers {{{1
class NoOpTask(nptask.Task):
    async_start = noop_async


class AsyncStartTask(nptask.Task):
    reclaim_task = noop_async
    run_task = noop_async
    upload_task = noop_async
    complete_task = noop_async


class NoReclaimTask(nptask.Task):
    reclaim_task = noop_async


class NoRunTask(nptask.Task):
    run_task = noop_async


@pytest.fixture(scope="function")
def claim_task():
    return {
        "runId": "0",
        "credentials": {},
        "status": {"taskId": "task_id"},
        "task": {"expires": arrow.get(0).isoformat(), "payload": {"uuid_manifest": "uuid_url"}},
    }


# task_credentials {{{1
@pytest.mark.asyncio
async def test_task_credentials(mocker, claim_task, config, event_loop):
    expected = {"foo": "bar"}
    claim_task["credentials"] = expected
    nooptask = NoOpTask(config, claim_task, event_loop=event_loop)
    nooptask.start()
    assert nooptask.task_credentials == expected


# async_start {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raises, expected_status",
    (
        (None, 0),
        (Download404, STATUSES["resource-unavailable"]),
        (DownloadError, STATUSES["intermittent-task"]),
        (RetryError, STATUSES["intermittent-task"]),
        (TaskError, STATUSES["malformed-payload"]),
        (asyncio.TimeoutError, STATUSES["resource-unavailable"]),
    ),
)
async def test_async_start(mocker, claim_task, config, event_loop, raises, expected_status):
    async def fake_run_task(*args):
        if raises:
            raise raises("foo")

    asynctask = AsyncStartTask(config, claim_task, event_loop=event_loop)
    asynctask.status = 0
    asynctask.run_task = fake_run_task
    asynctask.start()
    await asynctask.main_fut
    for fut in (asynctask.reclaim_fut, asynctask.task_fut):
        assert fut.cancelled() or fut.done()
    assert asynctask.complete
    assert asynctask.status == expected_status


# reclaim_task {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize("status_code, expected_status", ((409, STATUSES["superseded"]), (500, STATUSES["internal-error"])))
async def test_reclaim_task(mocker, claim_task, config, event_loop, status_code, expected_status):
    reclaim_status_codes = [None, status_code]

    async def fake_reclaim_task(*args, **kwargs):
        status = reclaim_status_codes.pop(0)
        if status:
            raise TaskclusterRestFailure("foo", None, status_code=status)
        return {}

    fake_queue = mocker.MagicMock()
    fake_queue.reclaimTask = fake_reclaim_task
    mocker.patch.object(asyncio, "sleep", new=noop_async)
    mocker.patch.object(nptask, "Queue", return_value=fake_queue)
    noruntask = NoRunTask(config, claim_task, event_loop=event_loop)
    noruntask.status = 0
    noruntask.start()
    await noruntask.reclaim_task()
    assert noruntask.status == expected_status


# upload_task {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,raises,expected_status",
    ((0, None, 0), (1, None, 1), (0, aiohttp.ClientError, STATUSES["intermittent-task"]), (0, KeyError, STATUSES["intermittent-task"]), (1, RetryError, 1)),
)
async def test_upload_task(mocker, config, claim_task, event_loop, status, raises, expected_status):
    async def fake_retry(*args, **kwargs):
        if raises:
            raise raises("foo")

    nooptask = NoOpTask(config, claim_task, event_loop=event_loop)
    nooptask.status = status
    nooptask.start()
    with open(nooptask.log_path, "w") as fh:
        print("foo", file=fh)
    mocker.patch.object(nptask, "retry_async", new=fake_retry)
    await nooptask.upload_task()
    assert nooptask.status == expected_status


# _upload_log {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize("response_status, raises", ((200, None), (204, None), (500, RetryError)))
async def test_upload_log(mocker, config, claim_task, event_loop, response_status, raises):
    nooptask = NoOpTask(config, claim_task, event_loop=event_loop)
    nooptask.status = 0
    nooptask.start()
    fake_resp = mocker.MagicMock()
    fake_resp.text = noop_async
    fake_resp.status = response_status

    async def fake_create_artifact(*args):
        return {"putUrl": "putUrl"}

    @asynccontextmanager
    async def fake_put(*args, **kwargs):
        yield fake_resp

    session = mocker.MagicMock()
    session.put = fake_put

    @asynccontextmanager
    async def fake_session(*args, **kwargs):
        yield session

    queue = mocker.MagicMock()
    queue.createArtifact = fake_create_artifact
    mocker.patch.object(nptask, "Queue", return_value=queue)
    mocker.patch.object(aiohttp, "ClientSession", new=fake_session)
    with open(nooptask.log_path, "w") as fh:
        print("foo", file=fh)
    if raises:
        with pytest.raises(raises):
            await nooptask._upload_log()
    else:
        await nooptask._upload_log()


# complete_task {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status, raises, result",
    (
        (0, None, "completed"),
        (1, None, "failed"),
        (2, None, "worker-shutdown"),
        (0, TaskclusterRestFailure("foo", None, status_code=409), None),
        (0, TaskclusterRestFailure("foo", None, status_code=500), None),
    ),
)
async def test_complete_task(mocker, config, claim_task, event_loop, status, raises, result):

    nooptask = NoOpTask(config, claim_task, event_loop=event_loop)
    nooptask.status = status
    nooptask._reclaim_task = {}

    async def fake_completed(*args):
        if raises:
            raise raises
        assert result == "completed"

    async def fake_failed(*args):
        assert result == "failed"

    async def fake_exception(task_id, run_id, payload):
        assert payload["reason"] == result

    queue = mocker.MagicMock()
    queue.reportCompleted = fake_completed
    queue.reportFailed = fake_failed
    queue.reportException = fake_exception
    mocker.patch.object(nptask, "Queue", return_value=queue)
    await nooptask.complete_task()


# task_log {{{1
def test_task_log(mocker, config, claim_task, event_loop):
    now = arrow.utcnow()
    nooptask = NoOpTask(config, claim_task, event_loop=event_loop)
    nooptask.start()
    mocker.patch.object(arrow, "utcnow", return_value=now)
    nooptask.task_log("foo")
    nooptask.task_log("bar", level=logging.ERROR)
    with open(nooptask.log_path, "r") as fh:
        contents = fh.read()
    assert (
        contents
        == """{now} INFO - foo
{now} ERROR - bar
""".format(
            now=now.format(config["task_log_datefmt"])
        )
    )


# download_uuids {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize("download_raises,json_raises", ((None, None), (Download404, None), (DownloadError, None), (None, TaskError)))
async def test_download_uuids(mocker, config, claim_task, event_loop, download_raises, json_raises):
    async def fake_download(*args, **kwargs):
        if download_raises:
            raise download_raises("foo")

    def fake_json(*args, **kwargs):
        if json_raises:
            raise json_raises("foo")
        return ["one", "two"]

    nooptask = NoOpTask(config, claim_task, event_loop=event_loop)
    mocker.patch.object(nptask, "retry_async", new=fake_download)
    mocker.patch.object(nptask, "load_json_or_yaml", new=fake_json)
    nooptask.start()
    if download_raises or json_raises:
        raises = download_raises if download_raises else json_raises
        with pytest.raises(raises):
            await nooptask.download_uuids()
    else:
        await nooptask.download_uuids()
        assert nooptask.uuids == ("one", "two")

    nooptask.claim_task["task"]["payload"] = {"uuids": ["asdf", "hjkl"]}
    await nooptask.download_uuids()
    assert nooptask.uuids == ("asdf", "hjkl")


# run_task {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "uuids, responses, expected_status, raises",
    (
        (["one", "two"], ["pending", "pending", "success", "success"], 0, False),
        (["one", "two"], ["broken", "success", "success"], 0, False),
        (["one", "two"], ["pending", "invalid"], STATUSES["failure"], TaskError),
    ),
)
async def test_run_task(mocker, config, claim_task, event_loop, uuids, responses, expected_status, raises):
    no_reclaim_task = NoReclaimTask(config, claim_task, event_loop=event_loop)
    no_reclaim_task.uuids = {u: False for u in uuids}
    no_reclaim_task.download_uuids = noop_async

    async def fake_run_command(*args, **kwargs):
        status = responses.pop(0)
        contents = """RequestUUID: feb8616e-e2e2-4621-bafc-3ef67fd86f6b
Date: 2019-12-13 18:05:41 +0000
Status: {}
LogFileURL: (null)
""".format(
            status
        )
        if status == "broken":
            contents = ""
        with open(no_reclaim_task.poll_log_path, "w") as fh:
            fh.write(contents)
        if status == "broken":
            return 1
        return 0

    mocker.patch.object(nptask, "run_command", new=fake_run_command)
    mocker.patch.object(asyncio, "sleep", new=noop_async)
    no_reclaim_task.async_start = noop_async
    no_reclaim_task.start()
    if raises:
        with pytest.raises(raises):
            await no_reclaim_task.run_task()
    else:
        await no_reclaim_task.run_task()
    assert no_reclaim_task.status == expected_status
