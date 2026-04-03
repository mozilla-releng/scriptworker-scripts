# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import pytest

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


@pytest.fixture
def hg_push_task():
    return {"payload": dict(HG_PUSH_PAYLOAD)}


@pytest.fixture
def cron_task():
    return {"payload": dict(CRON_PAYLOAD)}
