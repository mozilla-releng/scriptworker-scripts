from contextlib import contextmanager

from mock import ANY

import asyncio
import copy
import json
import mozapkpublisher
import os
import pytest
import sys

from unittest.mock import AsyncMock, create_autospec, MagicMock

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
            sgs_access_token=None,
            huawei_credentials=None,
            vivo_access_key=None,
            vivo_access_secret=None,
            vivo_basic_info_fallback=None
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
            sgs_access_token='456',
            huawei_credentials=None,
            vivo_access_key=None,
            vivo_access_secret=None,
            vivo_basic_info_fallback=None
        )


def test_huawei(monkeypatch):
    """The huawei branch of `push_apk` loads the credentials file and hands each package's
    APKs to `HuaweiAppGallery.upload_apks` with the requested rollout percentage."""
    mock_metadata = patch_extract_metadata(monkeypatch)
    huawei_mock = MagicMock()
    huawei_mock.return_value.__aenter__.return_value = huawei_mock
    huawei_mock.upload_apks = AsyncMock()
    monkeypatch.setattr('mozapkpublisher.push_apk.HuaweiAppGallery', huawei_mock)

    with NamedTemporaryFile('w', suffix='.json') as creds:
        json.dump({'key_id': 'key-from-file', 'sub_account': 'sub-from-file', 'private_key': 'pem-from-file'}, creds)
        creds.flush()

        asyncio.run(push_apk(
            APKS, None, [], 'production', store='huawei', rollout_percentage=25,
            contact_server=False, submit=True, huawei_credentials=creds.name,
        ))

    huawei_mock.assert_called_once_with(
        {'key_id': 'key-from-file', 'sub_account': 'sub-from-file', 'private_key': 'pem-from-file'}, dry_run=True
    )
    huawei_mock.upload_apks.assert_called_once_with(
        'org.mozilla.firefox',
        [(apk_arm, mock_metadata[apk_arm]), (apk_x86, mock_metadata[apk_x86])],
        25,
        submit=True,
    )


def test_main_huawei(monkeypatch):
    file = os.path.join(os.path.dirname(__file__), 'data', 'blob')
    test_args = [
        'script',
        '--store', 'huawei',
        '--huawei-credentials', '/path/to/creds.json',
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
            'huawei',
            None,
            True,
            True,
            False,
            False,
            False,
            False,
            submit=True,
            sgs_service_account_id=None,
            sgs_access_token=None,
            huawei_credentials='/path/to/creds.json',
            vivo_access_key=None,
            vivo_access_secret=None,
            vivo_basic_info_fallback=None
        )


def test_main_huawei_bad_args(monkeypatch):
    """--huawei-credentials is mandatory for --store=huawei, and argparse must be the one
    to reject it (exit code 2) rather than push_apk failing later."""
    file = os.path.join(os.path.dirname(__file__), 'data', 'blob')
    test_args = [
        'script',
        '--store', 'huawei',
        'alpha',
        file,
        '--expected-package-name=org.mozilla.fennec_aurora',
    ]

    monkeypatch.setattr(sys, 'argv', test_args)
    with pytest.raises(SystemExit) as exception:
        main()

    assert exception.value.code == 2


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


def test_vivo(monkeypatch):
    """The vivo branch of `push_apk` hands each package's APKs to
    `VivoAppStore.upload_apks`."""
    mock_metadata = patch_extract_metadata(monkeypatch)
    vivo_mock = MagicMock()
    vivo_mock.return_value.__aenter__.return_value = vivo_mock
    vivo_mock.upload_apks = AsyncMock()
    monkeypatch.setattr('mozapkpublisher.push_apk.VivoAppStore', vivo_mock)

    asyncio.run(push_apk(
        APKS, None, [], 'production', store='vivo', contact_server=False, submit=True,
        vivo_access_key='an-access-key', vivo_access_secret='an-access-secret',
    ))

    vivo_mock.assert_called_once_with('an-access-key', 'an-access-secret', dry_run=True, basic_info_fallback=None)
    vivo_mock.upload_apks.assert_called_once_with(
        'org.mozilla.firefox',
        [(apk_arm, mock_metadata[apk_arm]), (apk_x86, mock_metadata[apk_x86])],
        None,
        submit=True,
    )


def test_vivo_basic_info_fallback_reaches_the_store(monkeypatch):
    """The --vivo-* basic-info options are only read on a first-ever publish, so a broken
    link here would surface as a failed bootstrap rather than as a failing test."""
    patch_extract_metadata(monkeypatch)
    vivo_mock = MagicMock()
    vivo_mock.return_value.__aenter__.return_value = vivo_mock
    vivo_mock.upload_apks = AsyncMock()
    monkeypatch.setattr('mozapkpublisher.push_apk.VivoAppStore', vivo_mock)

    fallback = {'language_codes': 'en_in', 'nation_codes': 'in', 'email': 'release@mozilla.com'}
    asyncio.run(push_apk(
        APKS, None, [], 'production', store='vivo', contact_server=False,
        vivo_access_key='k', vivo_access_secret='s', vivo_basic_info_fallback=fallback,
    ))

    vivo_mock.assert_called_once_with('k', 's', dry_run=True, basic_info_fallback=fallback)


def test_vivo_without_credentials(monkeypatch):
    """Both halves of the key pair are needed; neither alone can sign a request."""
    patch_extract_metadata(monkeypatch)
    monkeypatch.setattr('mozapkpublisher.push_apk.VivoAppStore', MagicMock())

    for kwargs in ({}, {'vivo_access_key': 'k'}, {'vivo_access_secret': 's'}):
        with pytest.raises(RuntimeError, match='access key and access secret'):
            asyncio.run(push_apk(APKS, None, [], 'production', store='vivo', contact_server=False, **kwargs))


def test_main_vivo(monkeypatch):
    file = os.path.join(os.path.dirname(__file__), 'data', 'blob')
    test_args = [
        'script',
        '--store', 'vivo',
        '--vivo-access-key', 'an-access-key',
        '--vivo-access-secret', 'an-access-secret',
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
            'vivo',
            None,
            True,
            True,
            False,
            False,
            False,
            False,
            submit=True,
            sgs_service_account_id=None,
            sgs_access_token=None,
            huawei_credentials=None,
            vivo_access_key='an-access-key',
            vivo_access_secret='an-access-secret',
            vivo_basic_info_fallback=None
        )


def test_main_vivo_bad_args(monkeypatch):
    """Both --vivo-access-key and --vivo-access-secret are mandatory for --store=vivo, and
    argparse must be the one to reject them (exit code 2) rather than push_apk failing
    later."""
    file = os.path.join(os.path.dirname(__file__), 'data', 'blob')
    base_test_args = [
        'script',
        '--store', 'vivo',
        'alpha',
        file,
        '--expected-package-name=org.mozilla.fennec_aurora',
    ]

    for extra in (('--vivo-access-key', 'k'), ('--vivo-access-secret', 's'), ()):
        test_args = copy.copy(base_test_args)
        for (pos, extra_arg) in enumerate(extra):
            test_args.insert(pos + 1, extra_arg)

        monkeypatch.setattr(sys, 'argv', test_args)
        with pytest.raises(SystemExit) as exception:
            main()

        assert exception.value.code == 2


def test_main_vivo_basic_info_flags(monkeypatch):
    """The three --vivo-* basic-info options are collected into one fallback dict."""
    file = os.path.join(os.path.dirname(__file__), 'data', 'blob')
    test_args = [
        'script',
        '--store', 'vivo',
        '--vivo-access-key', 'k',
        '--vivo-access-secret', 's',
        '--vivo-language-codes', 'en_in,ms',
        '--vivo-nation-codes', 'in,id',
        '--vivo-email', 'release@mozilla.com',
        'production',
        file,
        '--expected-package-name=org.mozilla.fennec_aurora',
    ]

    with patch.object(mozapkpublisher.push_apk, 'push_apk') as mock_push_apk:
        monkeypatch.setattr(sys, 'argv', test_args)
        main()

        assert mock_push_apk.call_args.kwargs['vivo_basic_info_fallback'] == {
            'language_codes': 'en_in,ms',
            'nation_codes': 'in,id',
            'email': 'release@mozilla.com',
        }


def test_main_vivo_partial_basic_info_flags(monkeypatch):
    file = os.path.join(os.path.dirname(__file__), 'data', 'blob')
    test_args = [
        'script',
        '--store', 'vivo',
        '--vivo-access-key', 'k',
        '--vivo-access-secret', 's',
        '--vivo-language-codes', 'en_in',
        'production',
        file,
        '--expected-package-name=org.mozilla.fennec_aurora',
    ]

    with patch.object(mozapkpublisher.push_apk, 'push_apk') as mock_push_apk:
        monkeypatch.setattr(sys, 'argv', test_args)
        main()

        assert mock_push_apk.call_args.kwargs['vivo_basic_info_fallback'] == {'language_codes': 'en_in'}
