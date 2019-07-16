import pytest

import treescript.utils as utils
from treescript.exceptions import TaskVerificationError


TEST_ACTION_TAG = "project:releng:treescript:action:tagging"
TEST_ACTION_BUMP = "project:releng:treescript:action:version_bump"
TEST_ACTION_INVALID = "project:releng:treescript:action:invalid"

SCRIPT_CONFIG = {"taskcluster_scope_prefix": "project:releng:treescript:"}


# task_task_action_types {{{1
@pytest.mark.parametrize(
    "actions,scopes",
    (
        (["tagging"], [TEST_ACTION_TAG]),
        (["version_bump"], [TEST_ACTION_BUMP]),
        (["tagging", "version_bump"], [TEST_ACTION_BUMP, TEST_ACTION_TAG]),
    ),
)
def test_task_action_types_valid_scopes(actions, scopes):
    task = {"scopes": scopes}
    assert actions == utils.task_action_types(SCRIPT_CONFIG, task)


@pytest.mark.parametrize(
    "scopes", ([TEST_ACTION_INVALID], [TEST_ACTION_TAG, TEST_ACTION_INVALID])
)
def test_task_action_types_invalid_action(scopes):
    task = {"scopes": scopes}
    with pytest.raises(TaskVerificationError):
        utils.task_action_types(task, SCRIPT_CONFIG)


@pytest.mark.parametrize("scopes", ([], ["project:releng:foo:not:for:here"]))
def test_task_action_types_missing_action(scopes):
    task = {"scopes": scopes}
    with pytest.raises(TaskVerificationError):
        utils.task_action_types(task, SCRIPT_CONFIG)


@pytest.mark.parametrize(
    "task", ({"payload": {}}, {"payload": {"dry_run": False}}, {"scopes": ["foo"]})
)
def test_is_dry_run(task):
    assert False is utils.is_dry_run(task)


def test_is_dry_run_true():
    task = {"payload": {"dry_run": True}}
    assert True is utils.is_dry_run(task)
