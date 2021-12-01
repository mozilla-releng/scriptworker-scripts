import os

import pytest
from scriptworker_client import client

from pushmsixscript import artifacts, microsoft_store, task
from pushmsixscript.script import _log_warning_forewords, async_main

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


@pytest.mark.asyncio
async def test_async_main(monkeypatch):
    function_call_counter = (n for n in range(0, 2))

    config = {"push_to_store": True}
    msix_file_path = os.path.join(TEST_DATA_DIR, "valid-zip-valid-content.msix")
    monkeypatch.setattr(client, "get_task", lambda _: {})
    monkeypatch.setattr(artifacts, "get_msix_file_path", lambda c, t: msix_file_path)
    monkeypatch.setattr(task, "get_msix_channel", lambda config, channel: "release")

    def assert_push(config_, file_, channel):
        assert config_ == config
        assert file_ == msix_file_path
        assert channel == "release"
        next(function_call_counter)

    monkeypatch.setattr(microsoft_store, "push", assert_push)

    await async_main(config, {})

    assert next(function_call_counter) == 1


@pytest.mark.parametrize("is_allowed", (True, False))
def test_log_warning_forewords(caplog, monkeypatch, is_allowed):
    monkeypatch.setattr(task, "is_allowed_to_push_to_microsoft_store", lambda config, channel: is_allowed)
    _log_warning_forewords({}, channel="release")

    if is_allowed:
        assert not caplog.records
    else:
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "Insufficient rights to reach Microsoft Store: *All* requests will be mocked." in caplog.text
