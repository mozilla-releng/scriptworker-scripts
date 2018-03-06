import os
import tempfile
import shipitapi

from freezegun import freeze_time
from unittest.mock import MagicMock

from shipitscript.script import sync_main, async_main

this_dir = os.path.dirname(os.path.realpath(__file__))
project_dir = os.path.join(this_dir, '..', '..', '..')
project_data_dir = os.path.join(project_dir, 'shipitscript', 'data')


TASK_DEFINITION_TEMPLATE = '''{{
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
    "scopes": ["project:releng:ship-it:dev"],
    "payload": {{
        "release_name": "{release_name}"
    }}
}}'''


CONFIG_TEMPLATE = '''{{
    "work_dir": "{work_dir}",
    "schema_file": "{project_data_dir}/shipit_task_schema.json",
    "verbose": true,

    "ship_it_instances": {{
        "project:releng:ship-it:dev": {{
            "api_root": "http://some.ship-it.tld/api/root",
            "timeout_in_seconds": 1,
            "username": "some-username",
            "password": "some-password"
        }}
    }}
}}'''


@freeze_time('2018-01-22 17:59:59')
def test_main_mark_release_as_shipped(monkeypatch):
    ReleaseClassMock = MagicMock()
    release_instance_mock = MagicMock()
    ReleaseClassMock.side_effect = lambda *args, **kwargs: release_instance_mock
    monkeypatch.setattr(shipitapi, 'Release', ReleaseClassMock)

    with tempfile.TemporaryDirectory() as temp_dir:
        work_dir = os.path.join(temp_dir, 'work')
        os.makedirs(work_dir)
        config_path = os.path.join(temp_dir, 'config.json')
        with open(config_path, 'w') as config_file:
            config_file.write(
                CONFIG_TEMPLATE.format(work_dir=work_dir, project_data_dir=project_data_dir)
            )

        with open(os.path.join(work_dir, 'task.json'), 'w') as task_file:
            task_file.write(
                TASK_DEFINITION_TEMPLATE.format(release_name='Firefox-59.0b1-build1')
            )

        sync_main(async_main, config_path=config_path)

    ReleaseClassMock.assert_called_with(
        ('some-username', 'some-password'),
        api_root='http://some.ship-it.tld/api/root',
        timeout=1,
    )
    release_instance_mock.update.assert_called_with(
        'Firefox-59.0b1-build1', status='shipped', shippedAt='2018-01-22 17:59:59'
    )
