import json
import os
import tempfile
import shipitapi

from unittest.mock import MagicMock

from shipitscript.script import main

this_dir = os.path.dirname(os.path.realpath(__file__))
project_dir = os.path.join(this_dir, '..', '..', '..')
project_data_dir = os.path.join(project_dir, 'shipitscript', 'data')


MARK_AS_SHIPPED_TASK_DEFINITION_TEMPLATE = '''{{
    "provisionerId": "some-provisioner-id",
    "workerType": "some-worker-type",
    "schedulerId": "some-scheduler-id",
    "taskGroupId": "some-task-group-id",
    "routes": [],
    "retries": 5,
    "created": "2018-01-22T16:15:58.903Z",
    "deadline": "2018-01-22T18:15:59.010Z",
    "expires": "2019-01-22T18:15:59.010Z",
    "dependencies": ["aRandomTaskId1"],
    "scopes": [
        "project:releng:ship-it:server:dev",
        "project:releng:ship-it:action:mark-as-shipped"
    ],
    "payload": {{
        "release_name": "{release_name}"
    }}
}}'''

CONFIG_TEMPLATE = '''{{
    "work_dir": "{work_dir}",
    "mark_as_shipped_schema_file": "{project_data_dir}/mark_as_shipped_task_schema.json",
    "verbose": true,

    "ship_it_instances": {{
        "project:releng:ship-it:server:dev": {{
            "taskcluster_client_id": "some-id",
            "taskcluster_access_token": "some-token",
            "api_root_v2": "http://some.ship-it.tld/api/root-v2",
            "timeout_in_seconds": 1
        }}
    }},
    "taskcluster_scope_prefix": "project:releng:ship-it:"
}}'''


def test_main_mark_release_as_shipped_v2(monkeypatch):
    ReleaseClassMock = MagicMock()
    release_instance_mock = MagicMock()
    release_info = {
        'status': 'shipped',
    }
    attrs = {
        'getRelease.return_value': release_info
    }
    release_instance_mock.configure_mock(**attrs)
    ReleaseClassMock.side_effect = lambda *args, **kwargs: release_instance_mock
    monkeypatch.setattr(shipitapi, 'Release_V2', ReleaseClassMock)

    with tempfile.TemporaryDirectory() as temp_dir:
        work_dir = os.path.join(temp_dir, 'work')
        os.makedirs(work_dir)
        config_path = os.path.join(temp_dir, 'config.json')
        config_v2 = json.loads(
            CONFIG_TEMPLATE.format(work_dir=work_dir, project_data_dir=project_data_dir)
        )
        with open(config_path, 'w') as config_file:
            json.dump(config_v2, config_file)

        with open(os.path.join(work_dir, 'task.json'), 'w') as task_file:
            task_file.write(
                MARK_AS_SHIPPED_TASK_DEFINITION_TEMPLATE.format(release_name='Firefox-59.0b1-build1')
            )

        main(config_path=config_path)

    ReleaseClassMock.assert_called_with(
        api_root='http://some.ship-it.tld/api/root-v2',
        taskcluster_access_token='some-token', taskcluster_client_id='some-id',
        timeout=1
    )
    release_instance_mock.update_status.assert_called_with(
        'Firefox-59.0b1-build1', status='shipped'
    )
