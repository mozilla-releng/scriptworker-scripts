from scriptworker.context import Context
from scriptworker.exceptions import TaskVerificationError

import pushapkscript
import pytest
import os

from scriptworker import client, artifacts
from unittest.mock import MagicMock, patch

from pushapkscript import googleplay, jarsigner, task, manifest
from pushapkscript.exceptions import ConfigValidationError
from pushapkscript.script import async_main, get_default_config, main, _log_warning_forewords, _get_product_config, \
    _get_publish_config
from pushapkscript.test.helpers.mock_file import mock_open


@pytest.mark.asyncio
@pytest.mark.parametrize('android_product, update_google_play_strings, expected_strings_call_count', (
    ('aurora', True, 1),
    ('beta', True, 1),
    ('release', True, 1),
    ('dep', True, 1),
    ('focus', False, 0),
))
async def test_async_main(monkeypatch, android_product, update_google_play_strings, expected_strings_call_count):
    monkeypatch.setattr(
        artifacts,
        'get_upstream_artifacts_full_paths_per_task_id',
        lambda _: ({
            'someTaskId': ['/some/path/to/one.apk', '/some/path/to/another.apk'],
            'someOtherTaskId': ['/some/path/to/yet_another.apk', ],
        }, {})
    )
    monkeypatch.setattr(jarsigner, 'verify', lambda _, __, ___: None)
    monkeypatch.setattr(manifest, 'verify', lambda _, __: None)
    monkeypatch.setattr(task, 'extract_android_product_from_scopes', lambda _: android_product)
    monkeypatch.setattr(pushapkscript.script, '_get_product_config', lambda _, __: {
        'update_google_play_strings': update_google_play_strings,
        'apps': {
            android_product: {}
        }
    })

    google_play_strings_call_counter = (n for n in range(0, 2))

    def google_play_strings_call(_, __):
        string_path = None if android_product == 'focus' else '/some/path.json'
        next(google_play_strings_call_counter)
        return string_path

    monkeypatch.setattr(googleplay, 'get_google_play_strings_path', google_play_strings_call)

    context = MagicMock()
    context.config = {
        'do_not_contact_google_play': True
    }
    context.task = {
        'payload': {
            'channel': android_product
        }
    }

    def assert_google_play_call(_, __, ___, all_apks_files, ____, google_play_strings_file):
        assert sorted([file.name for file in all_apks_files]) == ['/some/path/to/another.apk', '/some/path/to/one.apk', '/some/path/to/yet_another.apk']
        if android_product == 'focus':
            assert google_play_strings_file is None
        else:
            assert google_play_strings_file.name == '/some/path.json'

    monkeypatch.setattr(googleplay, 'publish_to_googleplay', assert_google_play_call)

    with patch('pushapkscript.script.open', new=mock_open):
        await async_main(context)
    assert next(google_play_strings_call_counter) == expected_strings_call_count


def test_get_product_config_validation():
    context = Context()
    context.config = {}

    with pytest.raises(ConfigValidationError):
        _get_product_config(context, 'fenix')


def test_get_product_config_unknown_product():
    context = Context()
    context.config = {
        'products': [{
            'product_names': ['fenix']
        }]
    }

    with pytest.raises(TaskVerificationError):
        _get_product_config(context, 'unknown')


def test_get_product_config():
    context = Context()
    context.config = {
        'products': [{
            'product_names': ['fenix'],
            'foo': 'bar',
        }]
    }

    assert _get_product_config(context, 'fenix') == {'product_names': ['fenix'], 'foo': 'bar'}


def test_get_publish_config_fennec():
    aurora_config = {
        'use_scope_for_channel': True,
        'apps': {
            'aurora': {
                'google_play_track': 'beta',
                'certificate_alias': 'aurora'
            }
        }
    }
    assert _get_publish_config(aurora_config, {}, 'aurora') == {
        'certificate_alias': 'aurora',
        'google_play_track': 'beta',
    }


def test_get_publish_config_fennec_track_override():
    aurora_config = {
        'use_scope_for_channel': True,
        'apps': {
            'aurora': {
                'google_play_track': 'beta',
                'certificate_alias': 'aurora'
            }
        }
    }
    assert _get_publish_config(aurora_config, {'google_play_track': 'internal_qa'}, 'aurora') == {
        'certificate_alias': 'aurora',
        'google_play_track': 'internal_qa',
    }


def test_get_publish_config_fennec_rollout():
    aurora_config = {
        'use_scope_for_channel': True,
        'apps': {
            'aurora': {
                'google_play_track': 'beta',
                'certificate_alias': 'aurora'
            }
        }
    }
    assert _get_publish_config(aurora_config, {'rollout_percentage': 10}, 'aurora') == {
        'certificate_alias': 'aurora',
        'google_play_track': 'rollout',
        'rollout_percentage': 10,
    }


def test_get_publish_config_focus():
    focus_config = {
        'map_channels_to_tracks': True,
        'single_app_config': {
            'certificate_alias': 'focus'
        }
    }
    focus_payload = {'channel': 'beta'}
    assert _get_publish_config(focus_config, focus_payload, 'focus') == {
        'certificate_alias': 'focus',
        'google_play_track': 'beta',
    }


def test_get_publish_config_focus_rollout():
    focus_config = {
        'map_channels_to_tracks': True,
        'single_app_config': {
            'certificate_alias': 'focus'
        }
    }
    focus_payload = {
        'channel': 'rollout',
        'rollout_percentage': 10
    }
    assert _get_publish_config(focus_config, focus_payload, 'focus') == {
        'certificate_alias': 'focus',
        'google_play_track': 'rollout',
        'rollout_percentage': 10,
    }


def test_get_publish_config_fenix():
    fenix_config = {
        'apps': {
            'production': {
                'certificate_alias': 'fenix',
                'google_play_track': 'production',
            }
        }
    }
    fenix_payload = {'channel': 'production'}
    assert _get_publish_config(fenix_config, fenix_payload, 'focus') == {
        'certificate_alias': 'fenix',
        'google_play_track': 'production',
    }


def test_get_publish_config_fenix_rollout():
    fenix_config = {
        'apps': {
            'production': {
                'certificate_alias': 'fenix',
                'google_play_track': 'production',
            }
        }
    }
    fenix_payload = {
        'channel': 'production',
        'rollout_percentage': 10,
    }
    assert _get_publish_config(fenix_config, fenix_payload, 'focus') == {
        'certificate_alias': 'fenix',
        'google_play_track': 'rollout',
        'rollout_percentage': 10,
    }


def test_invalid_map_to_tracks_with_scope_as_channel():
    invalid_config = {
        'map_channels_to_tracks': True,
        'use_scope_for_channel': True,
        'single_app_config': {
            'certificate_alias': 'invalid',
        }
    }
    with pytest.raises(ValueError):
        _get_publish_config(invalid_config, {'google_play_track': 'rollout'}, 'scope-name')


@pytest.mark.parametrize('is_allowed_to_push, should_commit_transaction, expected', (
    (True, True, 'You will publish APKs to Google Play. This action is irreversible,\
if no error is detected either by this script or by Google Play.'),
    (True, False, 'APKs will be submitted to Google Play, but no change will not be committed.'),
    (False, False, 'This pushapk instance is not allowed to talk to Google Play. *All* requests will be mocked.'),
    (False, True, 'This pushapk instance is not allowed to talk to Google Play. *All* requests will be mocked.'),
))
def test_log_warning_forewords(caplog,  monkeypatch, is_allowed_to_push, should_commit_transaction, expected):
    monkeypatch.setattr(googleplay, 'should_commit_transaction', lambda _: should_commit_transaction)
    _log_warning_forewords(is_allowed_to_push, MagicMock())
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == 'WARNING'
    assert expected in caplog.text


def test_get_default_config():
    parent_dir = os.path.dirname(os.getcwd())
    assert get_default_config() == {
        'work_dir': os.path.join(parent_dir, 'work_dir'),
        'schema_file': os.path.join(os.path.dirname(pushapkscript.__file__), 'data/pushapk_task_schema.json'),
        'verbose': False,
    }


def test_main(monkeypatch):
    sync_main_mock = MagicMock()
    monkeypatch.setattr(client, 'sync_main', sync_main_mock)
    main()
    sync_main_mock.asset_called_once_with(async_main, default_config=get_default_config())
