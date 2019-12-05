import copy

import pytest
from scriptworker.exceptions import ScriptWorkerTaskException, TaskVerificationError

from shipitscript.task import _get_scope, get_ship_it_instance_config_from_scope, get_task_action, validate_task_schema


@pytest.mark.parametrize(
    "scopes,sufix,raises",
    (
        (("project:releng:ship-it:server:dev",), "server", False),
        (("project:releng:ship-it:server:staging",), "server", False),
        (("project:releng:ship-it:server:production",), "server", False),
        (("project:releng:ship-it:server:dev", "project:releng:ship-it:server:production"), "server", True),
        (("some:random:scope",), "server", True),
        (("project:releng:ship-it:action:mark-as-shipped",), "action", False),
        (("some:random:scope",), "action", True),
    ),
)
def test_get_scope(context, scopes, sufix, raises):
    context.task["scopes"] = scopes

    if raises:
        with pytest.raises(TaskVerificationError):
            _get_scope(context, sufix)
    else:
        assert _get_scope(context, sufix) == scopes[0]


@pytest.mark.parametrize(
    "api_root_v2, scope, raises",
    (
        ("https://localhost:8015", "project:releng:ship-it:server:dev", False),
        ("http://some-ship-it.url/v2", "project:releng:ship-it:server:dev", False),
        ("https://api.shipit.testing.mozilla-releng.net", "project:releng:ship-it:server:staging", False),
        ("https://api.shipit.testing.mozilla-releng.net/", "project:releng:ship-it:server:staging", False),
        ("https://shipit-api.mozilla-releng.net", "project:releng:ship-it:server:production", False),
        ("https://shipit-api.mozilla-releng.net/", "project:releng:ship-it:server:production", False),
    ),
)
def test_get_ship_it_instance_config_from_scope(context, api_root_v2, scope, raises):
    context.config["shipit_instance"] = copy.deepcopy(context.config["shipit_instance"])
    context.config["shipit_instance"]["scope"] = scope
    context.config["shipit_instance"]["api_root_v2"] = api_root_v2
    context.task["scopes"] = [scope]

    if raises:
        with pytest.raises(TaskVerificationError):
            get_ship_it_instance_config_from_scope(context)
    else:
        assert get_ship_it_instance_config_from_scope(context) == {
            "scope": scope,
            "api_root_v2": api_root_v2,
            "timeout_in_seconds": 1,
            "taskcluster_client_id": "some-id",
            "taskcluster_access_token": "some-token",
        }


@pytest.mark.parametrize("scope", ("some:random:scope", "project:releng:ship-it:server:staging", "project:releng:ship-it:server:production"))
def test_fail_get_ship_it_instance_config_from_scope(context, scope):
    context.task["scopes"] = [scope]
    with pytest.raises(TaskVerificationError):
        get_ship_it_instance_config_from_scope(context)


# validate_task {{{1
@pytest.mark.parametrize(
    "task,raises",
    (
        (
            {
                "dependencies": ["someTaskId"],
                "payload": {"release_name": "Firefox-59.0b3-build1"},
                "scopes": ["project:releng:ship-it:server:dev", "project:releng:ship-it:action:mark-as-shipped"],
            },
            False,
        ),
        (
            {
                "payload": {"release_name": "Firefox-59.0b3-build1"},
                "scopes": ["project:releng:ship-it:server:dev", "project:releng:ship-it:action:mark-as-shipped"],
            },
            True,
        ),
        ({"payload": {"release_name": "Firefox-59.0b3-build1"}, "scopes": ["project:releng:ship-it:server:dev"]}, True),
    ),
)
def test_validate_task(context, task, raises):
    context.task = task

    if raises:
        with pytest.raises(TaskVerificationError):
            validate_task_schema(context)
    else:
        validate_task_schema(context)


# get_task_action {{{1
@pytest.mark.parametrize(
    "scopes,expected,raises",
    ((("project:releng:ship-it:action:mark-as-random"), None, True), (("project:releng:ship-it:action:mark-as-shipped"), "mark-as-shipped", False)),
)
def test_get_task_action(context, scopes, expected, raises):
    context.task["scopes"] = [scopes]
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            get_task_action(context)
    else:
        assert expected == get_task_action(context)
