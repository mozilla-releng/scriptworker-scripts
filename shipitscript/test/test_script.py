import os
import pytest
import shipitscript
from unittest.mock import MagicMock

from scriptworker import client
from scriptworker.exceptions import TaskVerificationError, ScriptWorkerTaskException

from shipitscript import ship_actions, script
from shipitscript.test import context


assert context  # silence pyflakes


@pytest.mark.parametrize('scopes', (
    [
        'project:releng:ship-it:action:mark-as-shipped',
        'project:releng:ship-it:server:dev'
    ],
),)
@pytest.mark.asyncio
async def test_mark_as_shipped(context, monkeypatch, scopes):
    context.task['scopes'] = scopes

    mark_as_shipped_mock = MagicMock()
    mark_as_shipped_v2_mock = MagicMock()
    monkeypatch.setattr(ship_actions, 'mark_as_shipped', mark_as_shipped_mock)
    monkeypatch.setattr(ship_actions, 'mark_as_shipped_v2', mark_as_shipped_v2_mock)

    await script.async_main(context)
    mark_as_shipped_mock.assert_called_with({
        'api_root': 'http://some-ship-it.url',
        'api_root_v2': 'http://some-ship-it.url/v2',
        'timeout_in_seconds': 1,
        'taskcluster_client_id': 'some-id',
        'taskcluster_access_token': 'some-token',
        'username': 'some-username',
        'password': 'some-password'
    }, 'Firefox-59.0b3-build1')
    mark_as_shipped_v2_mock.assert_called_with({
        'api_root': 'http://some-ship-it.url',
        'api_root_v2': 'http://some-ship-it.url/v2',
        'timeout_in_seconds': 1,
        'taskcluster_client_id': 'some-id',
        'taskcluster_access_token': 'some-token',
        'username': 'some-username',
        'password': 'some-password'
    }, 'Firefox-59.0b3-build1')


@pytest.mark.parametrize('scopes,payload,raises', (
    ([
        'project:releng:ship-it:action:mark-as-started',
        'project:releng:ship-it:server:dev'
    ], {
        'release_name': 'Firefox-61.0b9-build1',
    }, True),
    ([
        'project:releng:ship-it:action:mark-as-started',
        'project:releng:ship-it:server:dev'
    ], {
        'release_name': 'Firefox-61.0b9-build1',
        'product': 'firefox',
        'version': '66.0b1',
        'build_number': 3,
        'branch': 'projects/maple',
        'l10n_changesets': 'ro default',
        'partials': '59.0b1build1,59.0b2build1',
        'revision': 'default',
    }, False),
))
@pytest.mark.asyncio
async def test_mark_as_started(context, monkeypatch, scopes, payload, raises):
    context.task['scopes'] = scopes
    context.task['payload'] = payload

    mark_as_started_mock = MagicMock()
    monkeypatch.setattr(ship_actions, 'mark_as_started', mark_as_started_mock)

    if raises:
        with pytest.raises(TaskVerificationError):
            await script.async_main(context)
    else:
        await script.async_main(context)
        mark_as_started_mock.assert_called_with({
            'api_root': 'http://some-ship-it.url',
            'api_root_v2': 'http://some-ship-it.url/v2',
            'timeout_in_seconds': 1,
            'taskcluster_client_id': 'some-id',
            'taskcluster_access_token': 'some-token',
            'username': 'some-username',
            'password': 'some-password'
        }, 'Firefox-61.0b9-build1', {
            'product': 'firefox',
            'version': '66.0b1',
            'buildNumber': 3,
            'branch': 'projects/maple',
            'l10nChangesets': 'ro default',
            'partials': '59.0b1build1,59.0b2build1',
            'mozillaRevision': 'default',
        })


@pytest.mark.parametrize('task,raises', (
    ({
        'dependencies': ['someTaskId'],
        'payload': {
            'release_name': 'Firefox-59.0b3-build1'
        },
        'scopes': [
            'project:releng:ship-it:server:dev',
            'project:releng:ship-it:action:mark-as-shipped',
        ],
    }, False),
    ({
        'dependencies': ['someTaskId'],
        'payload': {
            'release_name': 'Firefox-59.0b3-build1',
            'product': 'Firefox',
            'version': '61.0b8',
            'revision': 'aadufhgdgf54g89dfngjerhtirughdfg',
            'branch': 'maple',
            'build_number': 1,
            'l10n_changesets': 'ro default',
            'partials': '59.0b1build1,59.0b2build1',
        },
        'scopes': [
            'project:releng:ship-it:server:dev',
            'project:releng:ship-it:action:mark-as-started',
        ],
    }, False),
    ({
        'dependencies': ['someTaskId'],
        'payload': {
            'release_name': 'Firefox-59.0b3-build1',
            'product': 'Firefox',
            'version': '61.0b8',
            'revision': 'aadufhgdgf54g89dfngjerhtirughdfg',
            'branch': 'maple',
            'build_number': 1
        },
        'scopes': [
            'project:releng:ship-it:server:dev',
            'project:releng:ship-it:action:)hacK_mark-as-started38*&#F#BV&*',
        ],
    }, True)
))
@pytest.mark.asyncio
async def test_async_main(context, monkeypatch, task, raises):
    context.task = task

    mark_as_shipped_mock = MagicMock()
    monkeypatch.setattr(ship_actions, 'mark_as_shipped', mark_as_shipped_mock)
    mark_as_shipped_v2_mock = MagicMock()
    monkeypatch.setattr(ship_actions, 'mark_as_shipped_v2', mark_as_shipped_v2_mock)
    mark_as_started_mock = MagicMock()
    monkeypatch.setattr(ship_actions, 'mark_as_started', mark_as_started_mock)

    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            await script.async_main(context)
    else:
        await script.async_main(context)


def test_get_default_config():
    parent_dir = os.path.dirname(os.getcwd())
    data_dir = os.path.join(os.path.dirname(shipitscript.__file__), 'data')
    assert script.get_default_config() == {
        'work_dir': os.path.join(parent_dir, 'work_dir'),
        'verbose': False,
        'mark_as_shipped_schema_file': os.path.join(data_dir, 'mark_as_shipped_task_schema.json'),
        'mark_as_started_schema_file': os.path.join(data_dir, 'mark_as_started_task_schema.json'),
    }


def test_main(monkeypatch):
    sync_main_mock = MagicMock()
    monkeypatch.setattr(client, 'sync_main', sync_main_mock)
    script.main()
    sync_main_mock.asset_called_once_with(script.async_main,
                                          default_config=script.get_default_config())
