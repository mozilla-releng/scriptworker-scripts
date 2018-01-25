import pytest

from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException

from shipitscript.exceptions import TaskVerificationError
from shipitscript.script import get_default_config
from shipitscript.task import validate_task_schema, validate_task_scope, _get_scope


@pytest.fixture
def context():
    context = Context()
    context.config = get_default_config()
    context.config['ship_it_instance'] = {}
    context.task = {
        'dependencies': ['someTaskId'],
        'payload': {
            'release_name': 'Firefox-59.0b3-build1'
        },
        'scopes': ['project:releng:scriptworker:ship-it:dev'],
    }

    return context


def test_validate_task(context):
    validate_task_schema(context)

    context_with_no_scope = context
    context_with_no_scope.task['scopes'] = []
    with pytest.raises(ScriptWorkerTaskException):
        validate_task_schema(context_with_no_scope)


@pytest.mark.parametrize('api_root, scope, raises', (
    ('http://localhost:5000', 'project:releng:scriptworker:ship-it:dev', False),
    ('http://some-ship-it.url', 'project:releng:scriptworker:ship-it:dev', False),
    ('https://ship-it-dev.allizom.org', 'project:releng:scriptworker:ship-it:staging', False),
    ('https://ship-it-dev.allizom.org/', 'project:releng:scriptworker:ship-it:staging', False),
    ('https://ship-it.mozilla.org', 'project:releng:scriptworker:ship-it:production', False),
    ('https://ship-it.mozilla.org/', 'project:releng:scriptworker:ship-it:production', False),

    ('https://some-ship-it.url', 'project:releng:scriptworker:ship-it:production', True),
    ('https://some-ship-it.url', 'project:releng:scriptworker:ship-it:staging', True),
    # Dev scopes must not reach stage or prod
    ('https://ship-it-dev.allizom.org', 'project:releng:scriptworker:ship-it:dev', True),
    ('https://ship-it.mozilla.org', 'project:releng:scriptworker:ship-it:dev', True),
))
def test_validate_scope(context, api_root, scope, raises):
    context.config['ship_it_instance']['api_root'] = api_root
    context.task['scopes'] = [scope]

    if raises:
        with pytest.raises(TaskVerificationError):
            validate_task_scope(context)
    else:
        validate_task_scope(context)


@pytest.mark.parametrize('scopes, raises', (
    (('project:releng:scriptworker:ship-it:dev',), False),
    (('project:releng:scriptworker:ship-it:staging',), False),
    (('project:releng:scriptworker:ship-it:production',), False),
    (('project:releng:scriptworker:ship-it:dev', 'project:releng:scriptworker:ship-it:production',), True),
    (('project:releng:scriptworker:ship-it:unkown_scope',), True),
    (('some:random:scope',), True),
))
def test_get_scope(scopes, raises):
    task = {
        'scopes': scopes
    }

    if raises:
        with pytest.raises(TaskVerificationError):
            _get_scope(task)
    else:
        assert _get_scope(task) == scopes[0]
