import os
import pytest

from scriptworker import client
from unittest.mock import MagicMock

from shipitscript import ship_actions, task
from shipitscript.script import async_main, get_default_config, main


@pytest.mark.asyncio
async def test_async_main(monkeypatch):
    context = MagicMock()
    context.task = {
        'payload': {
            'release_name': 'Firefox-60.0-build1'
        }
    }
    monkeypatch.setattr(task, 'get_ship_it_instance_config_from_scope', lambda context: {
        'project:releng:ship-it:dev': {
            'api_root': 'http://some-ship-it.url',
            'timeout_in_seconds': 1,
            'username': 'some-username',
            'password': 'some-password'
        }
    })

    mark_as_shipped_mock = MagicMock()
    monkeypatch.setattr(ship_actions, 'mark_as_shipped', mark_as_shipped_mock)
    await async_main(context)
    mark_as_shipped_mock.assert_called_with({
        'project:releng:ship-it:dev': {
            'api_root': 'http://some-ship-it.url',
            'timeout_in_seconds': 1,
            'username': 'some-username',
            'password': 'some-password'
        }
    }, 'Firefox-60.0-build1')


def test_get_default_config():
    parent_dir = os.path.dirname(os.getcwd())
    assert get_default_config() == {
        'work_dir': os.path.join(parent_dir, 'work_dir'),
        'schema_file': os.path.join(os.getcwd(), 'shipitscript/data/shipit_task_schema.json'),
        'verbose': False,
    }


def test_main(monkeypatch):
    sync_main_mock = MagicMock()
    monkeypatch.setattr(client, 'sync_main', sync_main_mock)
    main()
    sync_main_mock.asset_called_once_with(async_main, default_config=get_default_config())
