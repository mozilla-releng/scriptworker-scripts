#!/usr/bin/env python
"""Notarization poller worker functions.

Attributes:
    log (logging.Logger): the log object for the module.

"""
import asyncio
import logging
import signal
import socket
import sys
import typing
from asyncio import sleep

import aiohttp
import arrow
import taskcluster
from taskcluster.aio import Queue

from notarization_poller.config import get_config_from_cmdln, update_logging_config
from notarization_poller.constants import MAX_CLAIM_WORK_TASKS
from notarization_poller.task import Task
from scriptworker_client.constants import STATUSES
from scriptworker_client.utils import makedirs, rm

log = logging.getLogger(__name__)


# claim_work {{{1
async def claim_work(config, worker_queue, num_tasks=1):
    """Find and claim the next pending task(s) in the queue, if any.

    Args:
        config (dict): the running config

    Returns:
        dict: a dict containing a list of the task definitions of the tasks claimed.

    """
    log.debug("Calling claimWork for {}/{}...".format(config["worker_group"], config["worker_id"]))
    payload = {"workerGroup": config["worker_group"], "workerId": config["worker_id"], "tasks": num_tasks}
    try:
        return await worker_queue.claimWork(config["provisioner_id"], config["worker_type"], payload)
    except (taskcluster.exceptions.TaskclusterFailure, aiohttp.ClientError) as exc:
        log.warning("{} {}".format(exc.__class__, exc))


# RunTasks {{{1
class RunTasks:
    """Manages processing of Taskcluster tasks."""

    def __init__(self, config):
        """Initialize RunTasks."""
        self.config = config
        self.running_tasks = []
        self.last_claim_work = arrow.get(0)
        self.is_stopped = False
        self.is_cancelled = False
        self.future = None

    async def invoke(self):
        """Claims and processes Taskcluster work."""
        while not self.is_cancelled and not self.is_stopped:
            num_tasks_to_claim = min(self.config["max_concurrent_tasks"] - len(self.running_tasks), MAX_CLAIM_WORK_TASKS)
            if num_tasks_to_claim > 0 and arrow.utcnow().timestamp - self.last_claim_work.timestamp >= self.config["claim_work_interval"]:
                async with aiohttp.ClientSession() as session:
                    queue = Queue(
                        options={
                            "credentials": {"accessToken": self.config["taskcluster_access_token"], "clientId": self.config["taskcluster_client_id"]},
                            "rootUrl": self.config["taskcluster_root_url"],
                        },
                        session=session,
                    )
                    new_tasks = await self._run_cancellable(claim_work(self.config, queue, num_tasks=num_tasks_to_claim)) or {}
                self.last_claim_work = arrow.utcnow()
                for claim_task in new_tasks.get("tasks", []):
                    new_task = Task(self.config, claim_task)
                    new_task.start()
                    self.running_tasks.append(new_task)
            await self.prune_running_tasks()
            sleep_time = self.last_claim_work.timestamp + self.config["claim_work_interval"] - arrow.utcnow().timestamp
            sleep_time > 0 and await self._run_cancellable(sleep(sleep_time))
        self.running_tasks and await asyncio.wait([task.main_fut for task in self.running_tasks if task.main_fut])

    async def prune_running_tasks(self):
        """Prune any complete tasks from ``self.running_tasks``."""
        for task in self.running_tasks:
            if task.complete:
                self.running_tasks.remove(task)

    async def _run_cancellable(self, coroutine: typing.Awaitable):
        if not self.is_cancelled:
            self.future = asyncio.ensure_future(coroutine)
            result = await self.future
            self.future = None
            return result

    async def cancel(self, status=STATUSES["worker-shutdown"]):
        """Cancel any running tasks."""
        self.is_cancelled = True
        self.future and self.future.cancel()
        try:
            for task in self.running_tasks:
                task.task_fut and task.task_fut.cancel()
            await asyncio.wait([task.main_fut for task in self.running_tasks if task.main_fut])
        except (asyncio.CancelledError, ValueError):
            pass


# main {{{1
def main(event_loop=None):
    """Notarization poller entry point: get everything set up, then enter the main loop.

    Args:
        event_loop (asyncio.BaseEventLoop, optional): the event loop to use.
            If None, use ``asyncio.get_event_loop()``. Defaults to None.

    """
    event_loop = event_loop or asyncio.get_event_loop()
    done = False
    config = get_config_from_cmdln(sys.argv[1:])
    update_logging_config(config)

    log.info("Notarization poller starting up at {} UTC".format(arrow.utcnow().format()))
    log.info("Worker FQDN: {}".format(socket.getfqdn()))
    rm(config["work_dir"])
    makedirs(config["work_dir"])
    running_tasks = RunTasks(config)

    async def _handle_sigterm():
        log.info("SIGTERM received; shutting down")
        nonlocal done
        done = True
        await running_tasks.cancel()

    async def _handle_sigusr1():
        """Stop accepting new tasks."""
        log.info("SIGUSR1 received; no more tasks will be taken")
        running_tasks.is_stopped = True

    event_loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.ensure_future(_handle_sigterm()))
    event_loop.add_signal_handler(signal.SIGUSR1, lambda: asyncio.ensure_future(_handle_sigusr1()))

    try:
        event_loop.run_until_complete(running_tasks.invoke())
    except Exception:
        log.critical("Fatal exception", exc_info=1)
        raise
    finally:
        log.info("Notarization poller stopped at {} UTC".format(arrow.utcnow().format()))
        log.info("Worker FQDN: {}".format(socket.getfqdn()))
