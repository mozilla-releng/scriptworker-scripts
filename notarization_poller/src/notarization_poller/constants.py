#!/usr/bin/env python
"""Notarization poller constants.

Attributes:
    DEFAULT_CONFIG (immutabledict): the default config for notarization poller.
        Running configs are validated against this.

"""
import os

from immutabledict import immutabledict
from scriptworker_client.constants import STATUSES

MAX_CLAIM_WORK_TASKS = 32

DEFAULT_CONFIG = immutabledict(
    {
        "log_datefmt": "%Y-%m-%dT%H:%M:%S",
        "task_log_datefmt": "YYYY-MM-DDTHH:mm:ss",
        "log_fmt": "%(asctime)s %(levelname)s - %(message)s",
        "log_dir": os.path.join(os.getcwd(), "logs"),
        "work_dir": os.path.join(os.getcwd(), "work"),
        "taskcluster_root_url": os.environ.get("TASKCLUSTER_ROOT_URL", "https://firefox-ci-tc.services.mozilla.com/"),
        "taskcluster_access_token": "...",
        "taskcluster_client_id": "...",
        "claim_work_interval": 30,
        "max_concurrent_tasks": 100,
        "reclaim_interval": 300,
        "artifact_upload_timeout": 120,
        "provisioner_id": "...",
        "worker_group": "...",
        "worker_type": "...",
        "worker_id": "...",
        "watch_log_file": False,
        "verbose": False,
        "xcrun_cmd": ("xcrun",),
        "notarization_username": "...",
        "notarization_password": "...",
        "poll_sleep_time": 30,
    }
)


# get_reversed_statuses {{{1
def get_reversed_statuses():
    """Return a mapping of exit codes to status strings.

    Returns:
        dict: the mapping of exit codes to status strings.

    """
    _rev = {v: k for k, v in STATUSES.items()}
    _rev.update({-11: "intermittent-task", -15: "intermittent-task"})
    return immutabledict(_rev)
