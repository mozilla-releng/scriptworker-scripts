import json
import os
import time

import pytest

import build_decision.hg_push as hg_push


@pytest.mark.parametrize(
    "pulse_payload, expected",
    (
        (
            # None if `pulse_payload["type"] != "changegroup.1"
            {"type": "unknown"},
            None,
        ),
        (
            # None if len(pushlog_pushes) == 0
            {"type": "changegroup.1", "data": {"pushlog_pushes": []}},
            None,
        ),
        (
            # None if len(pushlog_pushes) > 1
            {"type": "changegroup.1", "data": {"pushlog_pushes": ["one", "two"]}},
            None,
        ),
        (
            # None if len(heads) == 0
            {"type": "changegroup.1", "data": {"pushlog_pushes": ["one"], "heads": []}},
            None,
        ),
        (
            # None if len(heads) > 1
            {
                "type": "changegroup.1",
                "data": {"pushlog_pushes": ["one"], "heads": ["rev1", "rev2"]},
            },
            None,
        ),
        (
            # Success!
            {
                "type": "changegroup.1",
                "data": {"pushlog_pushes": ["one"], "heads": ["rev1"]},
            },
            "rev1",
        ),
    ),
)
def test_get_revision_from_pulse_message(mocker, pulse_payload, expected):
    """Add coverage for hg_push.get_revision_from_pulse_message."""
    pulse_message = json.dumps({"payload": pulse_payload})
    mocker.patch.object(os, "environ", new={"PULSE_MESSAGE": pulse_message})
    assert hg_push.get_revision_from_pulse_message() == expected


@pytest.mark.parametrize(
    "push_age, dry_run",
    (
        (
            # Ignore; too old
            hg_push.MAX_TIME_DRIFT + 5000,
            False,
        ),
        (
            # Don't ignore, dry run
            500,
            True,
        ),
        (
            # Don't ignore
            1000,
            False,
        ),
    ),
)
def test_build_decision(mocker, push_age, dry_run):
    """Add coverage for hg_push.build_decision."""
    taskcluster_root_url = "http://taskcluster.local"
    now_timestamp = 1649974668
    push = {"pushdate": now_timestamp - push_age}
    fake_repo = mocker.MagicMock()
    fake_repo.get_push_info.return_value = push
    fake_task = mocker.MagicMock()

    mocker.patch.object(
        os, "environ", new={"TASKCLUSTER_ROOT_URL": taskcluster_root_url}
    )
    mocker.patch.object(hg_push, "get_revision_from_pulse_message", return_value="rev")
    mocker.patch.object(time, "time", return_value=now_timestamp)
    mock_render = mocker.patch.object(hg_push, "render_tc_yml", return_value=fake_task)

    args = {
        "repository": fake_repo,
        "dry_run": dry_run,
    }

    hg_push.build_decision(**args)

    if not dry_run and push_age <= hg_push.MAX_TIME_DRIFT:
        fake_task.submit.assert_called_once_with()

        mock_render.assert_called_once()
        render_context = mock_render.call_args_list[0][1]
        assert render_context.pop("repository", False)
        assert render_context == {
            "push": {
                "pushdate": now_timestamp - push_age,
            },
            "taskcluster_root_url": taskcluster_root_url,
            "tasks_for": "hg-push",
        }
    else:
        fake_task.submit.assert_not_called()
