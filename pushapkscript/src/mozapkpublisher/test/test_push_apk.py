from contextlib import contextmanager

from mock import ANY

import mozapkpublisher
import os
import pytest
import sys

from unittest.mock import create_autospec, MagicMock

from tempfile import NamedTemporaryFile

from mozapkpublisher.common import store
from mozapkpublisher.common.exceptions import WrongArgumentGiven
from mozapkpublisher.push_apk import (
    push_apk,
    main,
    _apks_by_package_name,
)
from unittest.mock import patch


credentials = NamedTemporaryFile()
apk_x86 = NamedTemporaryFile()
apk_arm = NamedTemporaryFile()

APKS = [apk_x86, apk_arm]
SERVICE_ACCOUNT = 'foo@developer.gserviceaccount.com'
CLIENT_ID = 'client'
CLIENT_SECRET = 'secret'


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
    def fake_transaction(_, __, ___, *, contact_server, dry_run):
        yield mock_edit

    monkeypatch_.setattr(patch_target, 'transaction', fake_transaction)
    return mock_edit


def test_google_no_track():
    with pytest.raises(WrongArgumentGiven):
        push_apk(APKS, 'google', SERVICE_ACCOUNT, credentials, [])


def test_amazon_with_track():
    with pytest.raises(WrongArgumentGiven):
        push_apk(APKS, 'amazon', CLIENT_ID, CLIENT_SECRET, [], 'alpha')


def test_amazon_with_rollout():
    with pytest.raises(WrongArgumentGiven):
        push_apk(APKS, 'amazon', CLIENT_ID, CLIENT_SECRET, [], rollout_percentage=50)


def test_google(monkeypatch):
    mock_metadata = patch_extract_metadata(monkeypatch)
    edit_mock = patch_store_transaction(monkeypatch, store.GooglePlayEdit)
    push_apk(APKS, 'google', SERVICE_ACCOUNT, credentials, [], 'rollout', rollout_percentage=50,
             contact_server=False)
    edit_mock.update_app.assert_called_once_with([
        (apk_arm, mock_metadata[apk_arm]),
        (apk_x86, mock_metadata[apk_x86]),
    ], 'rollout', 50)


def test_amazon(monkeypatch):
    mock_metadata = patch_extract_metadata(monkeypatch)
    mock_edit = patch_store_transaction(monkeypatch, store.AmazonStoreEdit)

    push_apk(APKS, 'amazon', CLIENT_ID, CLIENT_SECRET, [], contact_server=False)
    mock_edit.update_app.assert_called_once_with([
        (apk_arm, mock_metadata[apk_arm]),
        (apk_x86, mock_metadata[apk_x86]),
    ])


def test_apks_by_package_name():
    one_package_apks_metadata = {
        apk_arm: {'package_name': 'org.mozilla.firefox'},
        apk_x86: {'package_name': 'org.mozilla.firefox'}
    }

    expected_one_package_metadata = {
        'org.mozilla.firefox': [
            (apk_arm, {'package_name': 'org.mozilla.firefox'}),
            (apk_x86, {'package_name': 'org.mozilla.firefox'}),
        ]
    }

    one_package_metadata = _apks_by_package_name(one_package_apks_metadata)
    assert len(one_package_metadata.keys()) == 1
    assert expected_one_package_metadata == one_package_metadata

    apk_arm_other = NamedTemporaryFile()
    two_package_apks_metadata = {
        apk_arm: {'package_name': 'org.mozilla.focus'},
        apk_x86: {'package_name': 'org.mozilla.focus'},
        apk_arm_other: {'package_name': 'org.mozilla.klar'}
    }

    expected_two_package_metadata = {
        'org.mozilla.klar': [
            (apk_arm_other, {'package_name': 'org.mozilla.klar'}),
        ],
        'org.mozilla.focus': [
            (apk_arm, {'package_name': 'org.mozilla.focus'}),
            (apk_x86, {'package_name': 'org.mozilla.focus'}),
        ]
    }

    two_package_metadata = _apks_by_package_name(two_package_apks_metadata)
    assert len(two_package_metadata.keys()) == 2
    assert expected_two_package_metadata == two_package_metadata


def test_push_apk_tunes_down_logs(monkeypatch):
    main_logging_mock = MagicMock()
    monkeypatch.setattr('mozapkpublisher.push_apk.main_logging', main_logging_mock)
    monkeypatch.setattr('mozapkpublisher.push_apk.extract_and_check_apks_metadata', MagicMock())
    monkeypatch.setattr('mozapkpublisher.push_apk._apks_by_package_name', MagicMock())

    push_apk(APKS, 'google', SERVICE_ACCOUNT, credentials, [], 'alpha', contact_server=False)

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
        '--username', 'foo@developer.gserviceaccount.com',
        '--secret', file,
        'google',
        'alpha',
        file,
        '--expected-package-name=org.mozilla.fennec_aurora',
    ]

    with patch.object(mozapkpublisher.push_apk, 'push_apk') as mock_push_apk:
        monkeypatch.setattr(sys, 'argv', fail_manual_validation_args)
        main()

        mock_push_apk.assert_called_once_with(
            ANY,
            'google',
            'foo@developer.gserviceaccount.com',
            file,
            ['org.mozilla.fennec_aurora'],
            'alpha',
            None,
            True,
            True,
            False,
            False,
            False,
            False,
        )


def test_main_amazon(monkeypatch):
    file = os.path.join(os.path.dirname(__file__), 'data', 'blob')
    fail_manual_validation_args = [
        'script',
        '--username', CLIENT_ID,
        '--secret', CLIENT_SECRET,
        'amazon',
        file,
        '--expected-package-name=org.mozilla.fennec_aurora',
    ]

    with patch.object(mozapkpublisher.push_apk, 'push_apk') as mock_push_apk:
        monkeypatch.setattr(sys, 'argv', fail_manual_validation_args)
        main()

        mock_push_apk.assert_called_once_with(
            ANY,
            'amazon',
            'client',
            'secret',
            ['org.mozilla.fennec_aurora'],
            None,
            None,
            True,
            True,
            False,
            False,
            False,
            False,
        )
