from scriptworker.context import Context
from scriptworker.exceptions import TaskVerificationError

import pushapkscript
import pytest
import os

from scriptworker import client, artifacts
from unittest.mock import MagicMock, patch

from pushapkscript import publish, jarsigner, task, manifest
from pushapkscript.exceptions import ConfigValidationError
from pushapkscript.script import async_main, get_default_config, main, _log_warning_forewords, _get_product_config
from pushapkscript.test.helpers.mock_file import mock_open


@pytest.mark.asyncio
@pytest.mark.parametrize('android_product', (
    'aurora',
    'beta',
    'release',
    'dep',
    'focus',
))
async def test_async_main(monkeypatch, android_product):
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
        'apps': {
            android_product: {
                'package_names': [android_product],
                'certificate_alias': android_product,
                'google': {
                    'default_track': 'beta',
                    'service_account': android_product,
                    'credentials_file': '{}.p12'.format(android_product),
                }
            }
        }
    })

    context = MagicMock()
    context.config = {
        'do_not_contact_google_play': True
    }
    context.task = {
        'payload': {
            'channel': android_product
        }
    }

    def assert_google_play_call(_, __, all_apks_files, ___):
        assert sorted([file.name for file in all_apks_files]) == ['/some/path/to/another.apk', '/some/path/to/one.apk', '/some/path/to/yet_another.apk']

    monkeypatch.setattr(publish, 'publish', assert_google_play_call)

    with patch('pushapkscript.script.open', new=mock_open):
        await async_main(context)


@pytest.mark.asyncio
async def test_async_main_no_signature_verify(monkeypatch):
    context = MagicMock()
    context.task['channel'] = 'release'

    # avoid running unrelated-to-this-test code
    monkeypatch.setattr(pushapkscript.script.task, 'extract_android_product_from_scopes', lambda _: 'firefox-tv')
    monkeypatch.setattr(pushapkscript.script, 'get_publish_config', lambda _, __, ___: {'dry_run': True, 'target_store': 'amazon'})
    monkeypatch.setattr(pushapkscript.script.publish, 'publish', lambda _, __, ___, ____: None)

    # set up "skip_check_signature
    monkeypatch.setattr(pushapkscript.script, '_get_product_config', lambda _, __: {'skip_check_signature': True})

    with patch.object(pushapkscript.script, 'jarsigner') as mock_jarsigner:
        with patch('pushapkscript.script.open', new=mock_open):
            await async_main(context)
        mock_jarsigner.assert_not_called()


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


@pytest.mark.parametrize('is_allowed_to_push, dry_run, target_store, expected', (
    (True, False, 'google', 'You will publish APKs to Google Play. This action is irreversible,\
if no error is detected either by this script or by Google Play.'),
    (True, True, 'google', 'APKs will be submitted, but no change will not be committed.'),
    (False, True, 'google', 'This pushapk instance is not allowed to talk to Google Play. *All* requests will be mocked.'),
    (False, False, 'google', 'This pushapk instance is not allowed to talk to Google Play. *All* requests will be mocked.'),
    (True, False, 'amazon', 'You will create a new "Upcoming Release" on Amazon. This release will not '
                            'be deployed until someone manually submits it on the Amazon web console.')
))
def test_log_warning_forewords(caplog,  monkeypatch, is_allowed_to_push, dry_run, target_store, expected):
    _log_warning_forewords(is_allowed_to_push, dry_run, target_store)
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
