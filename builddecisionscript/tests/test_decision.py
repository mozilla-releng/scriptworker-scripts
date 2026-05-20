import os
from unittest.mock import MagicMock, patch

import pytest

import build_decision.decision as decision


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
    # This will print() output; just exercise for coverage, for now.
    # We can capture STDOUT or mock print later if we want more real testing.
    task.display()


@pytest.mark.parametrize("proxy", (True, False))
def test_submit_task(proxy):
    """Add coverage for ``Task.submit``."""
    task_id = "asdf"
    task_payload = {"foo": "bar"}
    task = decision.Task(task_id=task_id, task_payload=task_payload)
    env = {}
    if proxy:
        env["TASKCLUSTER_PROXY_URL"] = "http://taskcluster"
    fake_queue = MagicMock()
    with patch.object(decision.taskcluster, "Queue", return_value=fake_queue):
        with patch.dict(os.environ, env, clear=True):
            task.submit()
    fake_queue.createTask.assert_called_once_with(task_id, task_payload)
