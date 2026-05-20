# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from unittest.mock import MagicMock, patch

import builddecisionscript.decision as decision
import pytest


@pytest.mark.parametrize(
    "tc_yml, raises, expected",
    (
        (
            {
                "tasks": [
                    {
                        "taskId": "one",
                        "key1": "value1",
                    },
                    {
                        "taskId": "two",
                        "key1": "value2",
                    },
                ],
            },
            True,
            None,
        ),
        (
            {
                "tasks": [],
            },
            True,
            None,
        ),
        (
            {
                "tasks": [
                    {
                        "taskId": "one",
                        "key1": "value1",
                    },
                ],
            },
            False,
            "one",
        ),
    ),
)
def test_render_tc_yml_exception(tc_yml, raises, expected):
    """Cause render_tc_yml to raise an exception for task_count != 1"""
    if raises:
        with pytest.raises(Exception):
            decision.render_tc_yml(tc_yml)
    else:
        task = decision.render_tc_yml(tc_yml)
        assert task.task_id == expected


def test_display_task():
    """Add coverage for ``Task.display``."""
    task = decision.Task(task_id="asdf", task_payload={"foo": "bar"})
    task.display()


def test_submit_task():
    """Add coverage for ``Task.submit``."""
    task_id = "asdf"
    task_payload = {"foo": "bar"}
    task = decision.Task(task_id=task_id, task_payload=task_payload)
    fake_queue = MagicMock()
    with patch.object(decision.taskcluster, "Queue", return_value=fake_queue):
        task.submit()
    fake_queue.createTask.assert_called_once_with(task_id, task_payload)
