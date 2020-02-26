#!/usr/bin/env python
# coding=utf-8
"""Test base files
"""
import arrow


def integration_create_task_payload(config, task_group_id, scopes=None, task_payload=None, task_extra=None):
    """For various integration tests, we need to call createTask for test tasks.

    This function creates a dummy payload for those createTask calls.
    """
    now = arrow.utcnow()
    deadline = now.shift(hours=1)
    expires = now.shift(days=3)
    scopes = scopes or []
    task_payload = task_payload or {}
    task_extra = task_extra or {}
    return {
        "provisionerId": config["provisioner_id"],
        "schedulerId": "test-dummy-scheduler",
        "workerType": config["worker_type"],
        "taskGroupId": task_group_id,
        "dependencies": [],
        "requires": "all-completed",
        "routes": [],
        "priority": "normal",
        "retries": 5,
        "created": now.isoformat(),
        "deadline": deadline.isoformat(),
        "expires": expires.isoformat(),
        "scopes": scopes,
        "payload": task_payload,
        "metadata": {
            "name": "Notarization Poller Integration Test",
            "description": "Notarization Poller Integration Test",
            "owner": "release+python@mozilla.com",
            "source": "https://github.com/mozilla-releng/scriptworker-scripts/",
        },
        "tags": {},
        "extra": task_extra,
    }


async def noop_async(*args, **kwargs):
    pass


def noop_sync(*args, **kwargs):
    pass


def create_async(result=None):
    async def fn(*args, **kwargs):
        return result

    return fn
