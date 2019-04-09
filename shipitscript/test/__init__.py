import os
import pytest

from scriptworker.context import Context


@pytest.fixture
def context():
    context = Context()
    context.config = {
        'mark_as_shipped_schema_file': os.path.join(os.getcwd(), 'shipitscript', 'data', 'mark_as_shipped_task_schema.json'),
    }
    context.config['ship_it_instances'] = {
        'project:releng:ship-it:server:dev': {
            'api_root_v2': 'http://some-ship-it.url/v2',
            'timeout_in_seconds': 1,
            'taskcluster_client_id': 'some-id',
            'taskcluster_access_token': 'some-token'
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
