import pytest
import os

from scriptworker import client
from unittest.mock import MagicMock

from pushapkscript import googleplay
from pushapkscript.script import async_main, get_default_config, main, _log_warning_forewords


@pytest.mark.parametrize('is_allowed_to_push, should_commit_transaction, expected', (
    (True, True, 'You will publish APKs to Google Play. This action is irreversible,\
if no error is detected either by this script or by Google Play.'),
    (True, False, 'APKs will be submitted to Google Play, but no change will not be committed.'),
    (False, False, 'You do not have the rights to reach Google Play. *All* requests will be mocked.'),
    (False, True, 'You do not have the rights to reach Google Play. *All* requests will be mocked.'),
))
def test_log_warning_forewords(caplog,  monkeypatch, is_allowed_to_push, should_commit_transaction, expected):
    monkeypatch.setattr(googleplay, 'is_allowed_to_push_to_google_play', lambda _: is_allowed_to_push)
    monkeypatch.setattr(googleplay, 'should_commit_transaction', lambda _: should_commit_transaction)
    _log_warning_forewords(MagicMock())
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == 'WARNING'
    assert expected in caplog.text


def test_get_default_config():
    parent_dir = os.path.dirname(os.getcwd())
    assert get_default_config() == {
        'work_dir': os.path.join(parent_dir, 'work_dir'),
        'schema_file': os.path.join(os.getcwd(), 'pushapkscript/data/pushapk_task_schema.json'),
        'verbose': False,
    }


def test_main(monkeypatch):
    sync_main_mock = MagicMock()
    monkeypatch.setattr(client, 'sync_main', sync_main_mock)
    main()
    sync_main_mock.asset_called_once_with(async_main, default_config=get_default_config())
