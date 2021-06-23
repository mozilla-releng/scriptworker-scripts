#!/usr/bin/env python
"""Task execution.

Attributes:
    NOTARIZATION_POLL_REGEX: the regex to find the notarization status
    Task (object): the task object
    log (logging.Logger): the log object for the module

"""

import asyncio
import gzip
import logging
import os
import pprint
import re
import traceback

import aiohttp
import arrow
import async_timeout
import taskcluster
import taskcluster.exceptions
from scriptworker_client.aio import download_file, retry_async
from scriptworker_client.constants import STATUSES
from scriptworker_client.exceptions import Download404, DownloadError, TaskError
from scriptworker_client.utils import load_json_or_yaml, makedirs, rm, run_command
from taskcluster.aio import Queue

from notarization_poller.constants import get_reversed_statuses
from notarization_poller.exceptions import RetryError

log = logging.getLogger(__name__)
NOTARIZATION_POLL_REGEX = re.compile(r"Status: (?P<status>success|invalid)")


class Task:
    """Manages all information related to a single running task."""

    reclaim_fut = None
    task_fut = None
    complete = False
    uuids = None

    def __init__(self, config, claim_task, event_loop=None):
        """Initialize Task."""
        self.config = config
        self.task_id = claim_task["status"]["taskId"]
        self.run_id = claim_task["runId"]
        self.claim_task = claim_task
        self.event_loop = event_loop or asyncio.get_event_loop()
        self.task_dir = os.path.join(self.config["work_dir"], "{}-{}".format(self.task_id, self.run_id))
        self.log_path = os.path.join(self.task_dir, "live_backing.log")
        self.poll_log_path = os.path.join(self.task_dir, "polling.log")

    def start(self):
        """Start the task."""
        rm(self.task_dir)
        makedirs(self.task_dir)
        self._reclaim_task = {}
        self.main_fut = self.event_loop.create_task(self.async_start())

    async def async_start(self):
        """Async start the task."""
        timeout = self.claim_task["task"]["payload"].get("maxRunTime")
        self.reclaim_fut = self.event_loop.create_task(self.reclaim_task())
        self.task_fut = self.event_loop.create_task(asyncio.wait_for(self.run_task(), timeout=timeout))

        try:
            await self.task_fut
        except Download404:
            self.status = STATUSES["resource-unavailable"]
            self.task_log(traceback.format_exc(), level=logging.CRITICAL)
        except (DownloadError, RetryError):
            self.status = STATUSES["intermittent-task"]
            self.task_log(traceback.format_exc(), level=logging.CRITICAL)
        except TaskError:
            self.status = STATUSES["malformed-payload"]
            self.task_log(traceback.format_exc(), level=logging.CRITICAL)
        except asyncio.CancelledError:
            # We already dealt with self.status in reclaim_task
            self.task_log(traceback.format_exc(), level=logging.CRITICAL)
        except asyncio.TimeoutError:
            self.status = STATUSES["resource-unavailable"]
            dependencies = self.claim_task["task"].get("dependencies", [])
            if len(dependencies) == 1:
                part1 = " (%s)" % dependencies[0]
            else:
                # we don't know which task is the right one, avoid giving bad advice
                part1 = ""
            self.task_log("Could not get notarization results back within %ss, you may need to force-rerun the notarization-part-1 task%s",
                          timeout, part1, level=logging.CRITICAL)
            self.task_log(traceback.format_exc(), level=logging.CRITICAL)
        log.info("Stopping task %s %s with status %s", self.task_id, self.run_id, self.status)
        self.reclaim_fut.cancel()
        await self.upload_task()
        await self.complete_task()
        rm(self.task_dir)
        self.complete = True

    @property
    def task_credentials(self):
        """Return the temporary credentials returned from [re]claimWork."""
        return self._reclaim_task.get("credentials", self.claim_task["credentials"])

    async def reclaim_task(self):
        """Try to reclaim a task from the queue.

        This is a keepalive.  Without it the task will expire and be re-queued.

        A 409 status means the task has been resolved. This generally means the
        task has expired, reached its deadline, or has been cancelled.

        Raises:
            TaskclusterRestFailure: on non-409 status_code from
                `taskcluster.aio.Queue.reclaimTask`

        """
        while True:
            log.debug("waiting %s seconds before reclaiming..." % self.config["reclaim_interval"])
            await asyncio.sleep(self.config["reclaim_interval"])
            log.debug("Reclaiming task %s %s", self.task_id, self.run_id)
            try:
                async with aiohttp.ClientSession() as session:
                    temp_queue = Queue(options={"credentials": self.task_credentials, "rootUrl": self.config["taskcluster_root_url"]}, session=session)
                    self._reclaim_task = await temp_queue.reclaimTask(self.task_id, self.run_id)
            except taskcluster.exceptions.TaskclusterRestFailure as exc:
                if exc.status_code == 409:
                    log.warning("Stopping task after receiving 409 response from reclaim_task: %s %s", self.task_id, self.run_id)
                    self.status = STATUSES["superseded"]
                else:
                    log.exception("reclaim_task unexpected exception: %s %s", self.task_id, self.run_id)
                    self.status = STATUSES["internal-error"]
                self.task_fut and self.task_fut.cancel()
                break

    async def upload_task(self):
        """Upload artifacts and return status.

        Returns the integer status of the upload. This only overrides
        ``status`` if ``status`` is 0 (success) and the upload fails.

        """
        try:
            with open(self.log_path, "rb") as f_in:
                text_content = f_in.read()
            with gzip.open(self.log_path, "wb") as f_out:
                f_out.write(text_content)
            await retry_async(self._upload_log, retry_exceptions=(KeyError, RetryError, TypeError, aiohttp.ClientError))
        except aiohttp.ClientError as e:
            self.status = self.status or STATUSES["intermittent-task"]
            log.error("Hit aiohttp error: {}".format(e))
        except Exception as e:
            self.status = self.status or STATUSES["intermittent-task"]
            log.exception("WORKER_UNEXPECTED_EXCEPTION upload {}".format(e))

    async def _upload_log(self):
        payload = {"storageType": "s3", "expires": arrow.get(self.claim_task["task"]["expires"]).isoformat(), "contentType": "text/plain"}
        args = [self.task_id, self.run_id, "public/logs/live_backing.log", payload]
        async with aiohttp.ClientSession() as session:
            temp_queue = Queue(options={"credentials": self.task_credentials, "rootUrl": self.config["taskcluster_root_url"]}, session=session)
            tc_response = await temp_queue.createArtifact(*args)
            headers = {aiohttp.hdrs.CONTENT_TYPE: "text/plain", aiohttp.hdrs.CONTENT_ENCODING: "gzip"}
            skip_auto_headers = [aiohttp.hdrs.CONTENT_TYPE]
            with open(self.log_path, "rb") as fh:
                async with async_timeout.timeout(self.config["artifact_upload_timeout"]):
                    async with session.put(tc_response["putUrl"], data=fh, headers=headers, skip_auto_headers=skip_auto_headers, compress=False) as resp:
                        log.info("create_artifact public/logs/live_backing.log: {}".format(resp.status))
                        response_text = await resp.text()
                        log.info(response_text)
                        if resp.status not in (200, 204):
                            raise RetryError("Bad status {}".format(resp.status))

    async def complete_task(self):
        """Submit task status to Taskcluster."""
        reversed_statuses = get_reversed_statuses()
        args = [self.task_id, self.run_id]
        try:
            async with aiohttp.ClientSession() as session:
                temp_queue = Queue(options={"credentials": self.task_credentials, "rootUrl": self.config["taskcluster_root_url"]}, session=session)
                if self.status == STATUSES["success"]:
                    log.info("Reporting task complete...")
                    response = await temp_queue.reportCompleted(*args)
                elif self.status != 1 and self.status in reversed_statuses:
                    reason = reversed_statuses[self.status]
                    log.info("Reporting task exception {}...".format(reason))
                    payload = {"reason": reason}
                    response = await temp_queue.reportException(*args, payload)
                else:
                    log.info("Reporting task failed...")
                    response = await temp_queue.reportFailed(*args)
                log.debug("Task status response:\n{}".format(pprint.pformat(response)))
        except taskcluster.exceptions.TaskclusterRestFailure as exc:
            if exc.status_code == 409:
                log.info("complete_task: 409: not reporting complete/failed for %s %s", self.task_id, self.run_id)
            else:
                log.exception("complete_task: unknown exception for %s %s", self.task_id, self.run_id)

    def task_log(self, msg, *args, level=logging.INFO, worker_log=True):
        """Log to ``self.log_path``.

        The ``log`` object is the logger for the entire worker, and will log
        information from ``n`` tasks. ``self.log_path`` should only contain
        information from this specific task.

        Args:
            msg (str): the message to log
            *args (list): any additional args to pass on to ``log.log``
            level (int): the logging level to use.
            worker_log (bool, optional): if True, also log to the worker log.
                Defaults to ``True``.

        """
        with open(self.log_path, "a") as log_fh:
            print(
                "{} {} - {}".format(arrow.utcnow().format(self.config["task_log_datefmt"]), logging._levelToName.get(level, str(level)), msg % args),
                file=log_fh,
            )
            worker_log and log.log(level, "%s:%s - {}".format(msg), self.task_id, self.run_id, *args)

    async def download_uuids(self):
        """Download the UUID manifest."""
        payload = self.claim_task["task"]["payload"]
        if payload.get("uuids"):
            # enable specifying uuids directly, for integration tests
            uuids = payload["uuids"]
        else:
            url = self.claim_task["task"]["payload"]["uuid_manifest"]
            path = os.path.join(self.task_dir, "uuids.json")
            self.task_log("Downloading %s", url)
            await retry_async(download_file, args=(url, path), retry_exceptions=(DownloadError,))
            uuids = load_json_or_yaml(path, is_path=True)
        self.uuids = tuple(uuids)
        self.task_log("UUIDs: %s", self.uuids)

    async def run_task(self):
        """Run the task, creating a task-specific log file."""
        self.status = 0
        username = self.config["notarization_username"]
        password = self.config["notarization_password"]

        await self.download_uuids()
        self.pending_uuids = list(self.uuids)
        while True:
            self.task_log("pending uuids: %s", self.pending_uuids)
            for uuid in sorted(self.pending_uuids):
                self.task_log("Polling %s", uuid)
                base_cmd = list(self.config["xcrun_cmd"]) + ["altool", "--notarization-info", uuid, "-u", username, "--password"]
                log_cmd = base_cmd + ["********"]
                rm(self.poll_log_path)
                status = await retry_async(
                    run_command,
                    args=[base_cmd + [password]],
                    kwargs={"log_path": self.poll_log_path, "log_cmd": log_cmd, "exception": RetryError},
                    retry_exceptions=(RetryError,),
                    attempts=10,
                )
                with open(self.poll_log_path, "r") as fh:
                    contents = fh.read()
                self.task_log("Polling response (status %d)", status, worker_log=False)
                for line in contents.splitlines():
                    self.task_log(" %s", line, worker_log=False)
                if status == STATUSES["success"]:
                    m = NOTARIZATION_POLL_REGEX.search(contents)
                    if m is not None:
                        if m["status"] == "invalid":
                            self.status = STATUSES["failure"]
                            self.task_log("Apple believes UUID %s is invalid!", uuid, level=logging.CRITICAL)
                            raise TaskError("Apple believes UUID %s is invalid!" % uuid)
                        # There are only two possible matches with the regex
                        # Adding `pragma: no branch` to be explicit in our
                        # checks, but still avoid testing an unreachable code
                        # branch
                        if m["status"] == "success":  # pragma: no branch
                            self.task_log("UUID %s is successful", uuid)
                            self.pending_uuids.remove(uuid)
            if len(self.pending_uuids) == 0:
                self.task_log("All UUIDs are successfully notarized: %s", self.uuids)
                break
            else:
                await asyncio.sleep(self.config["poll_sleep_time"])
