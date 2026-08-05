# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os

import builddecisionscript.cron.decision as decision
import pytest


@pytest.mark.parametrize(
    "job, expected",
    (
        ({}, []),
        (
            {
                "target-tasks-method": "target",
            },
            ["--target-tasks-method=target"],
        ),
        (
            {
                "target-tasks-method": "target",
                "include-push-tasks": True,
            },
            ["--target-tasks-method=target", "--include-push-tasks"],
        ),
        (
            {
                "optimize-target-tasks": ["one", "two"],
                "rebuild-kinds": ["three", "four"],
            },
            [
                "--optimize-target-tasks=['one', 'two']",
                "--rebuild-kind=three",
                "--rebuild-kind=four",
            ],
        ),
    ),
)
def test_make_arguments(job, expected):
    """Add coverage for cron.decision.make_arguments."""
    assert decision.make_arguments(job) == expected


@pytest.fixture
def run_decision_task(mocker):
    mocker.patch.object(os, "environ", new={"TASKCLUSTER_ROOT_URL": "http://taskcluster.local"})
    job_name = "abc"

    def inner(job=None, dry_run=False, cron_input=None):
        job = job or {}
        job.setdefault("treeherder-symbol", "x")

        mocks = {
            "hook": mocker.MagicMock(),
            "repo": mocker.MagicMock(),
            "render": mocker.MagicMock(),
        }
        mocks["repo"].get_file.return_value = {"tc": True}
        mocks["render"].return_value = mocks["hook"]

        mocker.patch.object(decision, "render_tc_yml", new=mocks["render"])
        mocker.patch.object(decision, "make_arguments", return_value=["--option=arg"])

        decision.run_decision_task(
            job_name,
            job,
            repository=mocks["repo"],
            push_info={"revision": "rev"},
            cron_input=cron_input,
            dry_run=dry_run,
        )

        return mocks

    return inner


@pytest.mark.parametrize("dry_run", (True, False))
def test_dry_run(run_decision_task, dry_run):
    """Add coverage for cron.decision.run_decision_task."""
    mocks = run_decision_task(dry_run=dry_run)

    if not dry_run:
        mocks["hook"].submit.assert_called_once_with()
    else:
        mocks["hook"].submit.assert_not_called()


def test_cron_input(run_decision_task):
    # No cron_input
    mock = run_decision_task()["render"]
    mock.assert_called_once()
    kwargs = mock.call_args_list[0][1]
    assert kwargs["cron"]["input"] == {}

    # cron_input provided but include-cron-input not set in job
    mock = run_decision_task(cron_input={"foo": "bar"})["render"]
    mock.assert_called_once()
    kwargs = mock.call_args_list[0][1]
    assert kwargs["cron"]["input"] == {}

    # cron_input provided and include-cron-input set
    mock = run_decision_task({"include-cron-input": True}, cron_input={"foo": "bar"})["render"]
    mock.assert_called_once()
    kwargs = mock.call_args_list[0][1]
    assert kwargs["cron"]["input"] == {"foo": "bar"}
