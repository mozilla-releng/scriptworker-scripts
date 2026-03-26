# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

from unittest.mock import patch

import pytest

_FAKE_TC_OPTIONS = {
    "rootUrl": "https://tc.example.com",
    "credentials": {
        "clientId": "test-client",
        "accessToken": "test-token",
    },
}


@pytest.fixture
def fake_taskcluster_options():
    with (
        patch(
            "builddecisionscript.decision.get_taskcluster_options",
            return_value=_FAKE_TC_OPTIONS,
        ),
        patch(
            "builddecisionscript.util.trigger_action.get_taskcluster_options",
            return_value=_FAKE_TC_OPTIONS,
        ),
        patch(
            "builddecisionscript.cron.action.get_taskcluster_options",
            return_value=_FAKE_TC_OPTIONS,
        ),
    ):
        yield

PULSE_MESSAGE = {
    "payload": {
        "type": "changegroup.1",
        "data": {
            "pushlog_pushes": [{"time": 1234567890, "push_full_json_url": "..."}],
            "heads": ["abc123def456"],
        },
    }
}

HG_PUSH_PAYLOAD = {
    "command": "hg-push",
    "repoUrl": "https://hg.mozilla.org/mozilla-central",
    "project": "mozilla-central",
    "level": "3",
    "repositoryType": "hg",
    "trustDomain": "gecko",
    "pulseMessage": PULSE_MESSAGE,
}

CRON_PAYLOAD = {
    "command": "cron",
    "repoUrl": "https://hg.mozilla.org/mozilla-central",
    "project": "mozilla-central",
    "level": "3",
    "repositoryType": "hg",
    "trustDomain": "gecko",
    "branch": "default",
}

HOOK_PAYLOAD = {
    "base_ref": None,
    "base_sha": "def456abc123def456abc123def456abc123def4",
    "owner": "dev@example.com",
    "ref": "refs/heads/main",
    "sha": "abc123def456abc123def456abc123def456abc1",
}

GIT_PUSH_PAYLOAD = {
    "command": "git-push",
    "repoUrl": "https://github.com/mozilla-releng/fxci-config",
    "project": "fxci-config",
    "level": "3",
    "repositoryType": "git",
    "trustDomain": "releng",
    "hookPayload": HOOK_PAYLOAD,
}


@pytest.fixture
def hg_push_task():
    return {"payload": dict(HG_PUSH_PAYLOAD)}


@pytest.fixture
def cron_task():
    return {"payload": dict(CRON_PAYLOAD)}


@pytest.fixture
def git_push_task():
    return {"payload": dict(GIT_PUSH_PAYLOAD)}
