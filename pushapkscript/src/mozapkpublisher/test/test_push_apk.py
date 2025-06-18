from contextlib import contextmanager

from mock import ANY

import copy
import mozapkpublisher
import os
import pytest
import sys

from unittest.mock import create_autospec, MagicMock

from tempfile import NamedTemporaryFile

from mozapkpublisher.common import store
from mozapkpublisher.push_apk import (
    push_apk,
    main,
)
from unittest.mock import patch


credentials = NamedTemporaryFile()
apk_x86 = NamedTemporaryFile()
apk_arm = NamedTemporaryFile()

APKS = [apk_x86, apk_arm]


def patch_extract_metadata(monkeypatch):
    mock_metadata = {
        apk_arm: {
            'architecture': 'armeabi-v7a',
            'firefox_build_id': '20171112125738',
            'version_code': '0',
            'package_name': 'org.mozilla.firefox',
            'locales': (
                'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-IN', 'br', 'ca', 'cak', 'cs', 'cy',
                'da', 'de', 'dsb', 'el', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR', 'es-CL',
                'es-ES',
                'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd', 'gl', 'gn',
                'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja', 'ka',
                'kab', 'kk', 'kn', 'ko', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my', 'nb-NO',
                'nl', 'nn-NO', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm', 'ro', 'ru', 'sk', 'sl',
                'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'uk', 'ur', 'uz', 'wo', 'xh',
                'zam', 'zh-CN', 'zh-TW',
            ),
            'api_level': 16,
            'firefox_version': '57.0',
        },
        apk_x86: {
            'architecture': 'x86',
            'firefox_build_id': '20171112125738',
            'version_code': '1',
            'package_name': 'org.mozilla.firefox',
            'locales': (
                'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-IN', 'br', 'ca', 'cak', 'cs', 'cy',
                'da', 'de', 'dsb', 'el', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR', 'es-CL',
                'es-ES',
                'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd', 'gl', 'gn',
                'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja', 'ka',
                'kab', 'kk', 'kn', 'ko', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my', 'nb-NO',
                'nl', 'nn-NO', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm', 'ro', 'ru', 'sk', 'sl',
                'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'uk', 'ur', 'uz', 'wo', 'xh',
                'zam', 'zh-CN', 'zh-TW',
            ),
            'api_level': 16,
            'firefox_version': '57.0',
        }
    }
    monkeypatch.setattr('mozapkpublisher.push_apk.extract_and_check_apks_metadata', lambda *args, **kwargs: mock_metadata)
    return mock_metadata


def patch_store_transaction(monkeypatch_, patch_target):
    mock_edit = create_autospec(patch_target)

    @contextmanager
    def fake_transaction(_, __, *, contact_server, dry_run):
        yield mock_edit

    monkeypatch_.setattr(patch_target, 'transaction', fake_transaction)
    return mock_edit


@pytest.mark.asyncio
async def test_google(monkeypatch):
    mock_metadata = patch_extract_metadata(monkeypatch)
    edit_mock = patch_store_transaction(monkeypatch, store.GooglePlayEdit)
    await push_apk(APKS, credentials, [], 'rollout', rollout_percentage=50,
                   contact_server=False)
    edit_mock.update_app.assert_called_once_with([
        (apk_arm, mock_metadata[apk_arm]),
        (apk_x86, mock_metadata[apk_x86]),
    ], 'rollout', 50)


@pytest.mark.asyncio
async def test_push_apk_tunes_down_logs(monkeypatch):
    main_logging_mock = MagicMock()
    monkeypatch.setattr('mozapkpublisher.push_apk.main_logging', main_logging_mock)
    monkeypatch.setattr('mozapkpublisher.push_apk.extract_and_check_apks_metadata', MagicMock())
    monkeypatch.setattr('mozapkpublisher.common.utils.metadata_by_package_name', MagicMock())

    await push_apk(APKS, credentials, [], 'alpha', contact_server=False)

    main_logging_mock.init.assert_called_once_with()


def test_main_bad_arguments_status_code(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['script'])
    with pytest.raises(SystemExit) as exception:
        main()
    assert exception.value.code == 2


def test_main_google(monkeypatch):
    file = os.path.join(os.path.dirname(__file__), 'data', 'blob')
    fail_manual_validation_args = [
        'script',
        '--secret', file,
        'alpha',
        file,
        '--expected-package-name=org.mozilla.fennec_aurora',
    ]

    with patch.object(mozapkpublisher.push_apk, 'push_apk') as mock_push_apk:
        monkeypatch.setattr(sys, 'argv', fail_manual_validation_args)
        main()

        mock_push_apk.assert_called_once_with(
            ANY,
            file,
            ['org.mozilla.fennec_aurora'],
            'alpha',
            'google',
            None,
            True,
            True,
            False,
            False,
            False,
            False,
            submit=False,
            sgs_service_account_id=None,
            sgs_access_token=None
        )


def test_main_samsung(monkeypatch):
    file = os.path.join(os.path.dirname(__file__), 'data', 'blob')
    test_args = [
        'script',
        '--store', 'samsung',
        '--sgs-service-account-id', '123',
        '--sgs-access-token', '456',
        '--submit',
        'alpha',
        file,
        '--expected-package-name=org.mozilla.fennec_aurora',
    ]

    with patch.object(mozapkpublisher.push_apk, 'push_apk') as mock_push_apk:
        monkeypatch.setattr(sys, 'argv', test_args)
        main()

        mock_push_apk.assert_called_once_with(
            ANY,
            None,
            ['org.mozilla.fennec_aurora'],
            'alpha',
            'samsung',
            None,
            True,
            True,
            False,
            False,
            False,
            False,
            submit=True,
            sgs_service_account_id='123',
            sgs_access_token='456'
        )


def test_main_samsung_bad_args(monkeypatch):
    file = os.path.join(os.path.dirname(__file__), 'data', 'blob')
    base_test_args = [
        'script',
        '--store', 'samsung',
        'alpha',
        file,
        '--expected-package-name=org.mozilla.fennec_aurora',
    ]

    for extra in (('--sgs-access-token', '456'), ('--sgs-service-account-id', '123'), ()):
        test_args = copy.copy(base_test_args)
        for (pos, extra_arg) in enumerate(extra):
            test_args.insert(pos + 1, extra_arg)

        monkeypatch.setattr(sys, 'argv', test_args)
        with pytest.raises(SystemExit) as exception:
            main()

        assert exception.value.code == 2
