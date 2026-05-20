import json
import os

import pytest
import taskcluster

import build_decision.cron.action as action


def test_find_decision_task(mocker):
    """Mock ``Index`` and return a task id."""
    find_task = {"taskId": "found_task_id"}
    fake_index = mocker.MagicMock()
    fake_index.findTask.return_value = find_task
    fake_repo = mocker.MagicMock()
    mocker.patch.object(taskcluster, "Index", return_value=fake_index)
    assert action.find_decision_task(fake_repo, "rev") == "found_task_id"


@pytest.mark.parametrize(
    "include_cron_input, extra_input, dry_run",
    (
        (False, False, False),
        (True, False, True),
        (False, True, False),
        (True, True, True),
    ),
)
def test_run_trigger_action(mocker, include_cron_input, extra_input, dry_run):
    """Add coverage to cron.action.run_trigger_action."""
    expected_input = {}
    job = {
        "action-name": "action",
    }
    env = {}
    if include_cron_input:
        job["include-cron-input"] = True
        cron_input = {"cron_input": {"one": "two"}}
        env["HOOK_PAYLOAD"] = json.dumps(cron_input)
        expected_input.update(cron_input)

    if extra_input:
        job["extra-input"] = {"extra_input": {"three": "four"}}
        expected_input.update(job["extra-input"])

    def fake_render_action(*, action_input, **kwargs):
        assert action_input == expected_input
        return fake_hook

    fake_hook = mocker.MagicMock()
    mocker.patch.object(os, "environ", new=env)
    mocker.patch.object(action, "find_decision_task", return_value="decision_task_id")
    mocker.patch.object(action, "render_action", new=fake_render_action)
    action.run_trigger_action(
        "action-name",
        job,
        repository=None,
        push_info={"revision": "rev"},
        dry_run=dry_run,
    )
    if not dry_run:
        fake_hook.submit.assert_called_once_with()
    else:
        fake_hook.submit.assert_not_called()
