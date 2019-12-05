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
import signal
import traceback

import aiohttp
import arrow
import async_timeout
import taskcluster
import taskcluster.exceptions
from taskcluster.aio import Queue
from taskcluster.client import createTemporaryCredentials

from notarization_poller.constants import get_reversed_statuses
from notarization_poller.exceptions import RetryError
from scriptworker_client.aio import download_file, retry_async
from scriptworker_client.constants import STATUSES
from scriptworker_client.exceptions import Download404, DownloadError, TaskError
from scriptworker_client.utils import load_json_or_yaml, makedirs, rm, run_command

log = logging.getLogger(__name__)
NOTARIZATION_POLL_REGEX = re.compile(r"Status: (?P<status>success|invalid)")


class Task:
    """Manages all information related to a single running task."""

    reclaim_fut = None
    task_fut = None
    complete = False
    process = None
    uuids = None

    def __init__(self, config, claim_task, event_loop=None):
        """Initialize Task."""
        self.config = config
        self.task_id = claim_task["status"]["taskId"]
        self.run_id = claim_task["runId"]
        self.claim_task = claim_task
        self.event_loop = event_loop or asyncio.get_event_loop()
        self.task_dir = os.path.join(config["work_dir"], self.task_id)
        self.log_path = os.path.join(self.task_dir, "live_backing.log")
        self.poll_log_path = os.path.join(self.task_dir, "polling.log")
        rm(self.task_dir)
        makedirs(self.task_dir)
        self.reclaim_fut = event_loop.create_task(self.reclaim_task())
        self._reclaim_task = {}
        self.task_fut = event_loop.create_task(self.run_task())

    @property
    def task_credentials(self):
        """Return the temporary credentials returned from [re]claimWork."""
        return self._reclaim_task.get("credentials", self.claim_task["credentials"])

    async def reclaim_task(self):
        """Try to reclaim a task from the queue.

        This is a keepalive.  Without it the task will expire and be re-queued.

        A 409 status means the task has been resolved.

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
                    self.reclaim_task = await temp_queue.reclaimTask(self.task_id, self.run_id)
            except taskcluster.exceptions.TaskclusterRestFailure as exc:
                if exc.status_code == 409:
                    log.warning("Stopping task %s %s after receiving 409 response from reclaim_task: %s %s", self.task_id, self.run_id)
                    exit_status = STATUSES["superseded"]
                else:
                    log.exception("reclaim_task unexpected exception: %s %s", self.task_id, self.run_id)
                    exit_status = STATUSES["internal-error"]
                await self.stop(status=exit_status)
                break

    async def stop(self, status=None, kill_run_task=True):
        """Stop the task."""
        if status is not None:
            self.status = status
        log.info("Stopping task %s %s with status %s", self.task_id, self.run_id, self.status)
        self.reclaim_fut and self.reclaim_fut.cancel()
        if kill_run_task and self.task_fut:
            self.task_fut.cancel()
        if self.process:
            pgid = -self.process.pid
            try:
                os.kill(pgid, signal.SIGTERM)
                await asyncio.sleep(1)
                os.kill(pgid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
        await self.upload_task()
        await self.complete_task()
        rm(self.task_dir)
        self.complete = True

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
            await retry_async(
                self._upload_log,
                retry_exceptions=(KeyError, RetryError, TypeError, aiohttp.ClientError),
                args=(self.log_path,),
                kwargs={"target_path": "public/logs/live_backing.log", "content_type": "text/plain", "content_encoding": "gzip"},
            )
        except aiohttp.ClientError as e:
            self.status = self.status or STATUSES["intermittent-task"]
            log.error("Hit aiohttp error: {}".format(e))
        except Exception as e:
            self.status = self.status or STATUSES["intermittent-task"]
            log.exception("WORKER_UNEXPECTED_EXCEPTION upload {}".format(e))

    async def _upload_log(self):
        payload = {"storageType": "s3", "expires": arrow.get(self.claim_task["task"]["expires"]).isoformat(), "contentType": "text/plain"}
        args = [self.task_id, self.run_id, self.log_path, payload]
        async with aiohttp.ClientSession() as session:
            temp_queue = Queue(options={"credentials": self.task_credentials, "rootUrl": self.config["taskcluster_root_url"]}, session=session)
            tc_response = await temp_queue.createArtifact(*args)
            headers = {aiohttp.hdrs.CONTENT_TYPE: "text/plain", aiohttp.hdrs.CONTENT_ENCODING: "gzip"}
            skip_auto_headers = [aiohttp.hdrs.CONTENT_TYPE]
            with open(self.log_path, "rb") as fh:
                async with async_timeout.timeout(self.config["artifact_upload_timeout"]):
                    async with session.put(tc_response["putUrl"], data=fh, headers=headers, skip_auto_headers=skip_auto_headers, compress=False) as resp:
                        log.info("create_artifact {}: {}".format(self.log_path, resp.status))
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
                if self.status == 0:
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
            print("{} {} - {}".format(arrow.utcnow().format(self.config["log_datefmt"]), logging._levelToName.get(level, str(level)), msg % args), file=log_fh)
            worker_log and log.log(level, "%s:%s - {}".format(msg), self.task_id, self.run_id, *args)

    async def download_uuids(self):
        """Download the UUID manifest."""
        url = self.claim_task["task"]["payload"]["uuid_manifest"]
        path = os.path.join(self.task_dir, "uuids.json")
        self.task_log("Downloading %s", url)
        try:
            await retry_async(download_file, args=(url, path), retry_exceptions=(DownloadError,))
        except Download404:
            self.status = STATUSES["resource-unavailable"]
            self.task_log(traceback.format_exc(), level=logging.CRITICAL)
            await self.stop()
        except DownloadError:
            self.status = STATUSES["intermittent-task"]
            self.task_log(traceback.format_exc(), level=logging.CRITICAL)
            await self.stop()
        try:
            uuids = load_json_or_yaml(path, is_path=True)
        except TaskError:
            self.status = STATUSES["malformed-payload"]
            self.task_log(traceback.format_exc(), level=logging.CRITICAL)
            await self.stop()
        self.uuids = {}
        for uuid in uuids:
            self.uuids[uuid] = False
        self.task_log("UUIDs: %s", self.uuids)

    async def run_task(self):
        """Run the task, creating a task-specific log file."""
        self.status = 0
        username = self.config["notarization_username"]
        password = self.config["notarization_password"]

        await self.download_uuids()
        done = False
        while not done:
            for uuid in [u for u in self.uuids if not self.uuids[u]]:
                base_cmd = ["xcrun", "altool", "--notarization-info", uuid, "-u", username, "--password"]
                log_cmd = base_cmd + ["********"]
                rm(self.poll_log_path)
                status = await run_command([base_cmd + [password]], log_cmd=log_cmd, log_path=self.poll_log_path)
                with open(self.poll_log_path, "r") as fh:
                    contents = fh.read()
                self.task_log("Polling response (status %d)", status, worker_log=False)
                for line in contents.splitlines():
                    self.task_log(" %s", line, worker_log=False)
                if status == 0:
                    m = NOTARIZATION_POLL_REGEX.search(contents)
                    if m is not None:
                        if m["status"] == "invalid":
                            self.status = STATUSES["failure"]
                            self.task_log("Apple believes UUID %s is invalid!", uuid, level=logging.CRITICAL)
                            done = True
                            break
                        # There are only two possible matches with the regex
                        # Adding `pragma: no branch` to be explicit in our
                        # checks, but still avoid testing an unreachable code
                        # branch
                        if m["status"] == "success":  # pragma: no branch
                            self.task_log("UUID %s is successful", uuid)
                            self.uuids[uuid] = True
            if all(self.uuids.values()):
                self.task_log("All UUIDs are successfully notarized: %s", self.uuids)
                break
            await asyncio.sleep(self.config["poll_sleep_time"])
        await self.stop(kill_run_task=False)


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


# create_temp_creds {{{1
def create_temp_creds(client_id, access_token, start=None, expires=None, scopes=None, name=None):
    """Request temp TC creds with our permanent creds.

    Args:
        client_id (str): the taskcluster client_id to use
        access_token (str): the taskcluster access_token to use
        start (str, optional): the datetime string when the credentials will
            start to be valid.  Defaults to 10 minutes ago, for clock skew.
        expires (str, optional): the datetime string when the credentials will
            expire.  Defaults to 31 days after 10 minutes ago.
        scopes (list, optional): The list of scopes to request for the temp
            creds.  Defaults to ['assume:project:taskcluster:worker-test-scopes', ]
        name (str, optional): the name to associate with the creds.

    Returns:
        dict: the temporary taskcluster credentials.

    """
    now = arrow.utcnow().shift(minutes=-10)
    start = start or now.datetime
    expires = expires or now.shift(days=31).datetime
    scopes = scopes or ["assume:project:taskcluster:worker-test-scopes"]
    creds = createTemporaryCredentials(client_id, access_token, start, expires, scopes, name=name)
    for key, value in creds.items():
        try:
            creds[key] = value.decode("utf-8")
        except (AttributeError, UnicodeDecodeError):
            pass
    return creds
