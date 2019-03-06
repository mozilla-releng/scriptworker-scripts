import json
import os
import tempfile
import shipitapi

from freezegun import freeze_time
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

MARK_AS_V1STARTED_TASK_DEFINITION_TEMPLATE = '''{{
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
        "project:releng:ship-it:action:mark-as-started"
    ],
    "payload": {{
        "release_name": "{release_name}",
        "product": "{product}",
        "version": "{version}",
        "build_number": {build_number},
        "branch": "{branch}",
        "l10n_changesets": "{l10n_changesets}",
        "partials": "{partials}",
        "revision": "{revision}"
    }}
}}'''

CONFIG_TEMPLATE = '''{{
    "work_dir": "{work_dir}",
    "mark_as_shipped_schema_file": "{project_data_dir}/mark_as_shipped_task_schema.json",
    "mark_as_started_schema_file": "{project_data_dir}/mark_as_started_task_schema.json",
    "verbose": true,

    "ship_it_instances": {{
        "project:releng:ship-it:server:dev": {{
            "taskcluster_client_id": "some-id",
            "taskcluster_access_token": "some-token",
            "api_root": "http://some.ship-it.tld/api/root",
            "api_root_v2": "http://some.ship-it.tld/api/root-v2",
            "timeout_in_seconds": 1,
            "username": "some-username",
            "password": "some-password"
        }}
    }},
    "taskcluster_scope_prefix": "project:releng:ship-it:"
}}'''


@freeze_time('2018-01-22 17:59:59')
def test_main_mark_release_as_shipped(monkeypatch):
    ReleaseClassMock = MagicMock()
    release_instance_mock = MagicMock()
    release_info = {
        'status': 'shipped',
        'shippedAt': '2018-01-22 17:59:59'
    }
    attrs = {
        'getRelease.return_value': release_info
    }
    release_instance_mock.configure_mock(**attrs)
    ReleaseClassMock.side_effect = lambda *args, **kwargs: release_instance_mock
    monkeypatch.setattr(shipitapi, 'Release', ReleaseClassMock)

    with tempfile.TemporaryDirectory() as temp_dir:
        work_dir = os.path.join(temp_dir, 'work')
        os.makedirs(work_dir)
        config_path = os.path.join(temp_dir, 'config.json')
        config_v1 = json.loads(
            CONFIG_TEMPLATE.format(work_dir=work_dir, project_data_dir=project_data_dir)
        )
        del config_v1['ship_it_instances']['project:releng:ship-it:server:dev']['api_root_v2']
        with open(config_path, 'w') as config_file:
            json.dump(config_v1, config_file)

        with open(os.path.join(work_dir, 'task.json'), 'w') as task_file:
            task_file.write(
                MARK_AS_SHIPPED_TASK_DEFINITION_TEMPLATE.format(release_name='Firefox-59.0b1-build1')
            )

        main(config_path=config_path)

    ReleaseClassMock.assert_called_with(
        ('some-username', 'some-password'),
        api_root='http://some.ship-it.tld/api/root',
        timeout=1,
    )
    release_instance_mock.update.assert_called_with(
        'Firefox-59.0b1-build1', status='shipped', shippedAt='2018-01-22 17:59:59'
    )


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
        del config_v2['ship_it_instances']['project:releng:ship-it:server:dev']['api_root']
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


def test_main_mark_release_as_started(monkeypatch):
    ReleaseClassMock = MagicMock()
    NewReleaseClassMock = MagicMock()
    release_instance_mock = MagicMock()
    release_info = {
        'status': 'Started',
        'ready': True,
        'complete': True,
    }
    attrs = {
        'getRelease.return_value': release_info
    }
    release_instance_mock.configure_mock(**attrs)
    new_release_instance_mock = MagicMock()
    ReleaseClassMock.side_effect = lambda *args, **kwargs: release_instance_mock
    NewReleaseClassMock.side_effect = lambda *args, **kwargs: new_release_instance_mock
    monkeypatch.setattr(shipitapi, 'Release', ReleaseClassMock)
    monkeypatch.setattr(shipitapi, 'NewRelease', NewReleaseClassMock)

    data = dict(
        product='firefox',
        version='99.0b1',
        buildNumber=1,
        branch='projects/maple',
        mozillaRevision='default',
        l10nChangesets='ro default',
        partials='98.0b1,98.0b14,98.0b15',
    )

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
                MARK_AS_V1STARTED_TASK_DEFINITION_TEMPLATE.format(
                    release_name='Firefox-59.0b1-build1',
                    product='firefox',
                    version='99.0b1',
                    build_number=1,
                    branch='projects/maple',
                    revision='default',
                    l10n_changesets='ro default',
                    partials='98.0b1,98.0b14,98.0b15'
                )
            )

        main(config_path=config_path)

    NewReleaseClassMock.assert_called_with(
        ('some-username', 'some-password'),
        api_root='http://some.ship-it.tld/api/root',
        timeout=1,
        csrf_token_prefix='firefox-'
    )
    new_release_instance_mock.submit.assert_called_with(**data)
