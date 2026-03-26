# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.


from builddecisionscript.hg_push import get_revision_from_pulse_message

PULSE_MESSAGE_CHANGEGROUP = {
    "payload": {
        "type": "changegroup.1",
        "data": {
            "pushlog_pushes": [{"time": 1234567890}],
            "heads": ["abc123def456"],
        },
    }
}


def test_get_revision_from_pulse_message():
    revision = get_revision_from_pulse_message(PULSE_MESSAGE_CHANGEGROUP)
    assert revision == "abc123def456"


def test_get_revision_wrong_type():
    msg = {
        "payload": {
            "type": "other.type",
            "data": {"pushlog_pushes": [{}], "heads": ["abc123"]},
        }
    }
    assert get_revision_from_pulse_message(msg) is None


def test_get_revision_multiple_pushes():
    msg = {
        "payload": {
            "type": "changegroup.1",
            "data": {
                "pushlog_pushes": [{"time": 1}, {"time": 2}],
                "heads": ["abc123"],
            },
        }
    }
    assert get_revision_from_pulse_message(msg) is None


def test_get_revision_multiple_heads():
    msg = {
        "payload": {
            "type": "changegroup.1",
            "data": {
                "pushlog_pushes": [{"time": 1}],
                "heads": ["abc123", "def456"],
            },
        }
    }
    assert get_revision_from_pulse_message(msg) is None
