#!/usr/bin/env python
# coding=utf-8
"""Test notarization_poller.worker
"""
import asyncio
import json
import os
import signal
import sys
from copy import deepcopy

import arrow
import pytest
from taskcluster.exceptions import TaskclusterRestFailure

import notarization_poller.worker as worker
from notarization_poller.exceptions import WorkerError
from notarization_poller.worker import RunTasks

from . import noop_async


# claim_work {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize("raises", (True, False))
async def test_claim_work(raises, config, mocker):
    async def foo(*args):
        raise TaskclusterRestFailure("foo", None, status_code=4)

    queue = mocker.MagicMock()
    if raises:
        queue.claimWork = foo
    else:
        queue.claimWork = noop_async
    assert await worker.claim_work(config, queue) is None


# main {{{1
def test_main(mocker, config, event_loop):
    async def foo(*args):
        raise WorkerError("foo")

    fake_run_tasks = mocker.MagicMock()
    fake_run_tasks.invoke = foo
    mocker.patch.object(worker, "RunTasks", return_value=fake_run_tasks)

    tmp = os.path.join(config["work_dir"], "foo")
    with open(tmp, "w") as fh:
        json.dump(config, fh)
    mocker.patch.object(sys, "argv", new=["x", tmp])
    with pytest.raises(WorkerError):
        worker.main(event_loop=event_loop)


@pytest.mark.parametrize("running", (True, False))
def test_main_running_sigterm(mocker, config, event_loop, running):
    """Test that sending SIGTERM causes the main loop to stop after the next
    call to invoke."""
    run_tasks_cancelled = event_loop.create_future()

    class MockRunTasks:
        async def cancel(*args):
            run_tasks_cancelled.set_result(True)

        async def invoke(*args):
            os.kill(os.getpid(), signal.SIGTERM)

    mrt = MockRunTasks()

    mocker.patch.object(worker, "RunTasks", return_value=mrt)

    tmp = os.path.join(config["work_dir"], "foo")
    with open(tmp, "w") as fh:
        json.dump(config, fh)
    mocker.patch.object(sys, "argv", new=["x", tmp])
    worker.main(event_loop=event_loop)

    if running:
        event_loop.run_until_complete(run_tasks_cancelled)
        assert run_tasks_cancelled.result()


@pytest.mark.parametrize("running", (True, False))
def test_main_running_sigusr1(mocker, config, event_loop, running):
    """Test that sending SIGUSR1 causes the main loop to stop after the next
    call to invoke without cancelling the task."""
    run_tasks_cancelled = event_loop.create_future()

    class MockRunTasks:
        is_stopped = False

        async def cancel(*args):
            run_tasks_cancelled.set_result(True)

        async def invoke(*args):
            os.kill(os.getpid(), signal.SIGUSR1)
            await asyncio.sleep(0.1)

    mrt = MockRunTasks()
    mrt.running_tasks = []
    if running:
        fake_task1 = mocker.MagicMock()
        fake_task1.main_fut = noop_async()
        fake_task2 = mocker.MagicMock()
        fake_task2.main_fut = noop_async()
        mrt.running_tasks = [fake_task1, fake_task2]

    tmp = os.path.join(config["work_dir"], "foo")
    with open(tmp, "w") as fh:
        json.dump(config, fh)
    mocker.patch.object(worker, "RunTasks", return_value=mrt)
    mocker.patch.object(sys, "argv", new=["x", tmp])
    worker.main(event_loop=event_loop)

    assert not run_tasks_cancelled.done()
    assert mrt.is_stopped


# invoke {{{1
@pytest.mark.asyncio
async def test_mocker_invoke(config, mocker):
    task = {"foo": "bar", "credentials": {"a": "b"}, "task": {"task_defn": True}}
    rt = worker.RunTasks(config)

    async def claim_work(*args, **kwargs):
        return {"tasks": [deepcopy(task)]}

    async def fake_sleep(*args, **kwargs):
        await asyncio.sleep(0.01)
        await rt.cancel()

    fake_task = mocker.MagicMock()
    fake_task.complete = False
    fake_task.main_fut = asyncio.ensure_future(noop_async())

    mocker.patch.object(worker, "claim_work", new=claim_work)
    mocker.patch.object(worker, "Task", return_value=fake_task)
    mocker.patch.object(worker, "Queue")
    mocker.patch.object(worker, "sleep", new=fake_sleep)
    await rt.invoke()
    assert rt.is_cancelled
    assert len(rt.running_tasks) == 1


@pytest.mark.asyncio
async def test_mocker_invoke_noop(config, mocker):
    config["max_concurrent_tasks"] = 0
    config["claim_work_interval"] = 30
    rt = RunTasks(config)
    rt.running_tasks = []
    # This is needed, or we'll never sleep, and cancel_rt will never
    # get a chance to run
    rt.last_claim_work = arrow.utcnow()

    async def cancel_rt():
        await rt.cancel()

    tasks = [asyncio.ensure_future(rt.invoke()), asyncio.ensure_future(cancel_rt())]
    await asyncio.wait(tasks)
    assert rt.is_cancelled
    assert len(rt.running_tasks) == 0


# prune_running_tasks {{{1
@pytest.mark.asyncio
async def test_prune_running_tasks(config, mocker):
    task1 = mocker.MagicMock()
    task1.complete = True
    task2 = mocker.MagicMock()
    task2.complete = False
    task3 = mocker.MagicMock()
    task3.complete = False
    task4 = mocker.MagicMock()
    task4.complete = True
    rt = RunTasks(config)
    rt.running_tasks = [task1, task2, task3, task4]
    await rt.prune_running_tasks()
    assert rt.running_tasks == [task2, task3]


# run_cancellable {{{1
@pytest.mark.asyncio
async def test_run_cancellable(config):
    async def return_true():
        return True

    rt = RunTasks(config)
    future1 = return_true()
    result = await rt._run_cancellable(future1)
    assert result is True

    # noop if is_cancelled
    rt.is_cancelled = True
    future2 = return_true()
    result = await rt._run_cancellable(future2)
    assert result is None
    await future2  # silence warnings
