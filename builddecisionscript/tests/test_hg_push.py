# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import os
import time

import builddecisionscript.hg_push as hg_push
import pytest


@pytest.mark.parametrize(
    "pulse_payload, expected",
    (
        (
            # None if `pulse_payload["type"] != "changegroup.1"`
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
def test_get_revision_from_pulse_message(pulse_payload, expected):
    """Add coverage for hg_push.get_revision_from_pulse_message."""
    pulse_message = {"payload": pulse_payload}
    assert hg_push.get_revision_from_pulse_message(pulse_message) == expected


@pytest.mark.parametrize(
    "push_age, use_tc_yml_repo, dry_run",
    (
        (
            # Ignore; too old
            hg_push.MAX_TIME_DRIFT + 5000,
            False,
            False,
        ),
        (
            # Don't ignore, dry run
            500,
            False,
            True,
        ),
        (
            # Don't ignore, use_tc_yml_repo
            1000,
            True,
            False,
        ),
    ),
)
def test_build_decision(mocker, push_age, use_tc_yml_repo, dry_run):
    """Add coverage for hg_push.build_decision."""
    taskcluster_root_url = "http://taskcluster.local"
    now_timestamp = 1649974668
    push = {"pushdate": now_timestamp - push_age}
    fake_repo = mocker.MagicMock()
    fake_repo.get_push_info.return_value = push
    fake_tc_yml_repo = mocker.MagicMock()
    fake_task = mocker.MagicMock()

    mocker.patch.object(os, "environ", new={"TASKCLUSTER_ROOT_URL": taskcluster_root_url})
    mocker.patch.object(time, "time", return_value=now_timestamp)
    mock_render = mocker.patch.object(hg_push, "render_tc_yml", return_value=fake_task)

    pulse_message = {
        "payload": {
            "type": "changegroup.1",
            "data": {"pushlog_pushes": ["one"], "heads": ["rev"]},
        }
    }

    hg_push.build_decision(
        repository=fake_repo,
        taskcluster_yml_repo=fake_tc_yml_repo if use_tc_yml_repo else None,
        pulse_message=pulse_message,
        dry_run=dry_run,
    )

    if not dry_run and push_age <= hg_push.MAX_TIME_DRIFT:
        fake_task.submit.assert_called_once_with()

        mock_render.assert_called_once()
        render_kwargs = mock_render.call_args_list[0][1]
        assert render_kwargs.pop("repository", False)
        assert render_kwargs == {
            "push": {
                "pushdate": now_timestamp - push_age,
            },
            "taskcluster_root_url": taskcluster_root_url,
            "tasks_for": "hg-push",
        }
    else:
        fake_task.submit.assert_not_called()
