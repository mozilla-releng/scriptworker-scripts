import pytest

from scriptworker.exceptions import ScriptWorkerTaskException

from bouncerscript.task import (
    get_supported_actions, get_task_server, get_task_action, validate_task_schema,
)
from bouncerscript.test import (
    submission_context
)


assert submission_context  # silence pyflakes


# get_task_server {{{1
@pytest.mark.parametrize("scopes,expected,raises", ((
    ["project:releng:bouncer:server:staging",
     "project:releng:bouncer:server:production"],
    None, True,
), (
    ["project:releng:bouncer:server:!!"],
    None, True
), (
    ["project:releng:bouncer:server:staging",
     "project:releng:bouncer:action:foo"],
    "project:releng:bouncer:server:staging", False
)))
def test_get_task_server(scopes, expected, raises):
    task = {'scopes': scopes}
    config = {'bouncer_config': {'project:releng:bouncer:server:staging': ''}}
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            get_task_server(task, config)
    else:
        assert expected == get_task_server(task, config)


# get_task_action {{{1
@pytest.mark.parametrize("scopes,expected,raises", ((
    ["project:releng:bouncer:action:submission",
     "project:releng:bouncer:action:aliases"],
    None, True
), (
    ["project:releng:bouncer:action:invalid"],
    None, True
), (
    ["project:releng:bouncer:action:submission"],
    "submission", False
), (
    ["project:releng:bouncer:action:aliases"],
    "aliases", False
)))
def test_get_task_action(scopes, expected, raises):
    task = {'scopes': scopes}
    config = {
        'schema_files': {
            'submission': '/some/path.json',
            'aliases': '/some/other_path.json',
        },
    }
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            get_task_action(task, config)
    else:
        assert expected == get_task_action(task, config)


def test_get_supported_actions():
    config = {
        'schema_files': {
            'submission': '/some/path.json',
            'aliases': '/some/other_path.json',
        },
    }
    assert sorted(get_supported_actions(config)) == sorted(('submission', 'aliases'))


def test_validate_task_schema(submission_context, schema="submission"):
    validate_task_schema(submission_context)
