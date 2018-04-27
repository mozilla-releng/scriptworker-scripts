import pytest
import os

from scriptworker import client, artifacts
from unittest.mock import MagicMock

from pushapkscript import googleplay, jarsigner, task
from pushapkscript.script import async_main, get_default_config, main, _log_warning_forewords


@pytest.mark.asyncio
@pytest.mark.parametrize('android_product, expected_strings_call_count', (
    ('aurora', 1),
    ('beta', 1),
    ('release', 1),
    ('dep', 1),
    ('focus', 0),
))
async def test_async_main(monkeypatch, android_product, expected_strings_call_count):
    monkeypatch.setattr(
        artifacts,
        'get_upstream_artifacts_full_paths_per_task_id',
        lambda _: ({
            'someTaskId': ['/some/path/to/one.apk', '/some/path/to/another.apk'],
            'someOtherTaskId': ['/some/path/to/yet_another.apk', ],
        }, {})
    )
    monkeypatch.setattr(googleplay, 'is_allowed_to_push_to_google_play', lambda _: False)
    monkeypatch.setattr(jarsigner, 'verify', lambda _, __: None)
    monkeypatch.setattr(task, 'extract_android_product_from_scopes', lambda _: android_product)

    google_play_strings_call_counter = (n for n in range(0, 2))

    def google_play_strings_call(_, __):
        string_path = None if android_product == 'focus' else '/some/path.json'
        next(google_play_strings_call_counter)
        return string_path

    monkeypatch.setattr(googleplay, 'get_google_play_strings_path', google_play_strings_call)

    context = {'fake': 'context'}

    def assert_google_play_call(context, all_apks_paths, google_play_strings_path):
        assert context == {'fake': 'context'}
        assert sorted(all_apks_paths) == ['/some/path/to/another.apk', '/some/path/to/one.apk', '/some/path/to/yet_another.apk']
        if android_product == 'focus':
            assert google_play_strings_path is None
        else:
            assert google_play_strings_path == '/some/path.json'

    monkeypatch.setattr(googleplay, 'publish_to_googleplay', assert_google_play_call)

    await async_main(context)
    assert next(google_play_strings_call_counter) == expected_strings_call_count


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
