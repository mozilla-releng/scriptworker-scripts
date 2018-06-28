import os
import pytest

from scriptworker.context import Context


@pytest.fixture
def context():
    context = Context()
    context.config = {
        'mark_as_shipped_schema_file': os.path.join(os.getcwd(), 'shipitscript', 'data', 'mark_as_shipped_task_schema.json'),
        'mark_as_started_schema_file': os.path.join(os.getcwd(), 'shipitscript', 'data', 'mark_as_started_task_schema.json')
    }
    context.config['ship_it_instances'] = {
        'project:releng:ship-it:server:dev': {
            'api_root': 'http://some-ship-it.url',
            'timeout_in_seconds': 1,
            'username': 'some-username',
            'password': 'some-password'
        }
    }
    context.config['taskcluster_scope_prefix'] = "project:releng:ship-it:"
    context.task = {
        'dependencies': ['someTaskId'],
        'payload': {
            'release_name': 'Firefox-59.0b3-build1'
        },
        'scopes': ['project:releng:ship-it:server:dev'],
    }

    return context
