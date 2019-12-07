#!/usr/bin/env python
"""scriptworker constants.

Attributes:
    DEFAULT_CONFIG (frozendict): the default config for scriptworker.  Running configs
        are validated against this.

"""
import os

from frozendict import frozendict

from scriptworker_client.constants import STATUSES

DEFAULT_CONFIG = frozendict(
    {
        "log_datefmt": "%Y-%m-%dT%H:%M:%S",
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
    return frozendict(_rev)
