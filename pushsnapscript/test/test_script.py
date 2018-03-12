import pytest

from scriptworker import client
from unittest.mock import MagicMock

from pushsnapscript import artifacts, task
from pushsnapscript.script import async_main


@pytest.mark.asyncio
async def test_hello_world(capsys, monkeypatch):
    monkeypatch.setattr(client, 'get_task', lambda _: {})
    monkeypatch.setattr(artifacts, 'get_snap_file_path', lambda _: '/some/file.snap')
    monkeypatch.setattr(task, 'pluck_channel', lambda _: 'edge')
    context = MagicMock()

    await async_main(context)

    captured = capsys.readouterr()
    assert captured.out == '/some/file.snap edge\n'
    assert captured.err == ''
