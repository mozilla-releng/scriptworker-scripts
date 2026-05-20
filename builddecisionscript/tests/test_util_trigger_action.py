import io
import json
import os

import pytest
import requests
import taskcluster

import build_decision.util.scopes as scopes
import build_decision.util.trigger_action as trigger_action

from . import TEST_DATA_DIR


@pytest.mark.parametrize(
    "context, task_tags, expected",
    (
        (
            [
                {
                    "tag1": "required_value1",
                    "tag2": "required_value2",
                },
                {
                    "tag3": "required_value3",
                    "tag4": "required_value4",
                },
            ],
            {
                "tag2": "different_value2",
                "tag3": "required_value3",
                "tag4": "required_value4",
            },
            True,
        ),
        (
            [
                {
                    "tag1": "required_value1",
                    "tag2": "required_value2",
                },
                {
                    "tag3": "required_value3",
                    "tag4": "required_value4",
                },
            ],
            {
                "tag2": "different_value2",
                "tag3": "different_value3",
                "tag4": "required_value4",
            },
            False,
        ),
        (
            [
                {
                    "tag1": "required_value1",
                    "tag2": "required_value2",
                },
                {
                    "tag3": "required_value3",
                    "tag4": "required_value4",
                },
            ],
            {
                "tag2": "required_value2",
                "tag3": "required_value3",
            },
            False,
        ),
    ),
)
def test_is_task_in_context(context, task_tags, expected):
    """Compare context tag sets vs task tags."""
    assert trigger_action._is_task_in_context(context, task_tags) == expected


@pytest.mark.parametrize(
    "original_task, expected_action_names",
    (
        (
            None,
            {
                "add-new-jobs",
                "cancel-all",
                "release-promotion",
                "retrigger-multiple",
            },
        ),
        (
            {
                "tags": {
                    "kind": "cron-task",
                },
            },
            {
                "rerun",
                "retrigger",
                "cancel",
            },
        ),
    ),
)
def test_filter_relevant_actions(original_task, expected_action_names):
    """Compare task tags against action.json's actions."""
    with open(TEST_DATA_DIR / "actions.json") as fh:
        actions_json = json.load(fh)
    relevant_actions = trigger_action._filter_relevant_actions(
        actions_json, original_task
    )
    assert set(relevant_actions.keys()) == expected_action_names


@pytest.mark.parametrize("raises", (None, RuntimeError))
def test_check_decision_task_scopes(mocker, raises):
    """Test how the function raises if scopes match or not."""

    def fake_satisfies(*args, **kwargs):
        # We test `scopes.satisfies` elsewhere; we're just testing the raise and
        # adding coverage.
        return not raises

    mocker.patch.object(trigger_action, "taskcluster")
    mocker.patch.object(scopes, "satisfies", new=fake_satisfies)

    if raises:
        with pytest.raises(raises):
            trigger_action._check_decision_task_scopes(
                "decision_task_id", "hook_group_id", "hook_id"
            )
    else:
        assert (
            trigger_action._check_decision_task_scopes(
                "decision_task_id", "hook_group_id", "hook_id"
            )
            is None
        )


@pytest.mark.parametrize(
    "actions, action_name, task_id, action_input, raises",
    (
        (
            # add-new-jobs should work for `task_id` `None`
            None,
            "add-new-jobs",
            None,
            {},
            False,
        ),
        (
            # retrigger should work for a non-None `task_id`
            None,
            "retrigger",
            "task_id",
            {},
            False,
        ),
        (
            # Die on invalid actions_json version
            {"version": "invalid_version"},
            "retrigger",
            "task_id",
            {},
            RuntimeError,
        ),
        (
            # Retrigger isn't in `relevant_actions` if `task_id` is `None`
            None,
            "retrigger",
            None,
            {},
            LookupError,
        ),
        (
            # NotImplementedError if the action kind is not "hook"
            {
                "version": 1,
                "actions": [
                    {
                        "context": [],
                        "kind": "invalid_kind!!!",
                        "name": "fake_action",
                    }
                ],
            },
            "fake_action",
            None,
            {},
            NotImplementedError,
        ),
    ),
)
def test_render_action(mocker, actions, action_name, task_id, action_input, raises):
    """Add coverage to ``render_action``, largely testing the raises."""

    class fake_session:
        def get(*args):
            r = requests.Response()
            r.status_code = 200
            r.encoding = "utf-8"
            r.headers["content-type"] = "application/json"
            if actions is not None:
                r.raw = io.BytesIO(json.dumps(actions).encode("utf-8"))
            else:
                r.raw = open(TEST_DATA_DIR / "actions.json", "rb")
            return r

    fake_queue = mocker.MagicMock()
    fake_hook = mocker.MagicMock()
    mocker.patch.object(taskcluster, "Queue", return_value=fake_queue)
    mocker.patch.object(trigger_action, "Hook", new=fake_hook)
    mocker.patch.object(trigger_action, "_check_decision_task_scopes")
    mocker.patch.object(trigger_action, "SESSION", new=fake_session())

    if raises:
        with pytest.raises(raises):
            trigger_action.render_action(
                action_name=action_name,
                task_id=task_id,
                decision_task_id="decision_task_id",
                action_input=action_input,
            )
    else:
        trigger_action.render_action(
            action_name=action_name,
            task_id=task_id,
            decision_task_id="decision_task_id",
            action_input=action_input,
        )


def test_hook_display():
    """Add coverage to Hook.display.

    Since it's only print commands, just run it.
    """
    hook = trigger_action.Hook(
        hook_group_id="group_id",
        hook_id="id",
        hook_payload={},
    )
    hook.display()


@pytest.mark.parametrize("has_proxy_url", (True, False))
def test_hook_submit(mocker, has_proxy_url):
    """Add coverage to Hook.submit"""

    env = {}
    if has_proxy_url:
        env["TASKCLUSTER_PROXY_URL"] = "fake_proxy_urL"

    mocker.patch.object(os, "environ", new=env)
    mocker.patch.object(taskcluster, "Hooks")
    hook = trigger_action.Hook(
        hook_group_id="group_id",
        hook_id="id",
        hook_payload={},
    )
    hook.submit()
