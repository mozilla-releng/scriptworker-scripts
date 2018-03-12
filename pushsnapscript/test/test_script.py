import pytest

from scriptworker import client
from unittest.mock import MagicMock

from pushsnapscript import artifacts, task, snap_store
from pushsnapscript.script import async_main


@pytest.mark.asyncio
async def test_async_main(monkeypatch):
    function_call_counter = (n for n in range(0, 2))

    context = MagicMock()
    monkeypatch.setattr(client, 'get_task', lambda _: {})
    monkeypatch.setattr(artifacts, 'get_snap_file_path', lambda _: '/some/file.snap')
    monkeypatch.setattr(task, 'pluck_channel', lambda _: 'edge')

    def assert_push(context_, file_, channel):
        assert context_ == context
        assert file_ == '/some/file.snap'
        assert channel == 'edge'
        next(function_call_counter)

    monkeypatch.setattr(snap_store, 'push', assert_push)

    await async_main(context)

    assert next(function_call_counter) == 1
