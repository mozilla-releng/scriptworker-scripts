import pytest

from scriptworker import client
from unittest.mock import MagicMock

from pushsnapscript import artifacts, task, snap_store
from pushsnapscript.script import async_main, _log_warning_forewords


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


@pytest.mark.parametrize('is_allowed', (True, False))
def test_log_warning_forewords(caplog, monkeypatch, is_allowed):
    monkeypatch.setattr(task, 'is_allowed_to_push_to_snap_store', lambda _: is_allowed)
    _log_warning_forewords(context=MagicMock())

    if is_allowed:
        assert not caplog.records
    else:
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == 'WARNING'
        assert 'You do not have the rights to reach Snap store. *All* requests will be mocked.' in caplog.text
