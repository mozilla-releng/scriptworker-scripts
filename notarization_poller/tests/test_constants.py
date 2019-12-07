#!/usr/bin/env python
# coding=utf-8
"""Test notarization_poller.constants
"""
from frozendict import frozendict

import notarization_poller.constants as constants


def test_get_reversed_statuses():
    assert constants.get_reversed_statuses() == frozendict(
        {
            0: "success",
            1: "failure",
            2: "worker-shutdown",
            3: "malformed-payload",
            4: "resource-unavailable",
            5: "internal-error",
            6: "superseded",
            7: "intermittent-task",
            -11: "intermittent-task",
            -15: "intermittent-task",
        }
    )
