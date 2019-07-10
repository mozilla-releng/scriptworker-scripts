import mozapkpublisher
import os
import pytest
import sys

from unittest.mock import create_autospec, MagicMock

from tempfile import NamedTemporaryFile

from mozapkpublisher.common import googleplay
from mozapkpublisher.common.exceptions import WrongArgumentGiven
from mozapkpublisher.push_apk import (
    push_apk,
    main,
    _get_ordered_version_codes,
    _split_apk_metadata_per_package_name,
)
from unittest.mock import patch


credentials = NamedTemporaryFile()
apk_x86 = NamedTemporaryFile()
apk_arm = NamedTemporaryFile()

APKS = [apk_x86, apk_arm]
SERVICE_ACCOUNT = 'foo@developer.gserviceaccount.com'


@pytest.fixture
def edit_service_mock():
    return create_autospec(googleplay.EditService)


def set_up_mocks(monkeypatch_, edit_service_mock_):
    def _metadata(*args, **kwargs):
        return {
            apk_arm.name: {
                'architecture': 'armeabi-v7a',
                'firefox_build_id': '20171112125738',
                'version_code': '0',
                'package_name': 'org.mozilla.firefox',
                'locales': (
                    'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-IN', 'br', 'ca', 'cak', 'cs', 'cy',
                    'da', 'de', 'dsb', 'el', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR', 'es-CL', 'es-ES',
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
            apk_x86.name: {
                'architecture': 'x86',
                'firefox_build_id': '20171112125738',
                'version_code': '1',
                'package_name': 'org.mozilla.firefox',
                'locales': (
                    'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-IN', 'br', 'ca', 'cak', 'cs', 'cy',
                    'da', 'de', 'dsb', 'el', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR', 'es-CL', 'es-ES',
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

    monkeypatch_.setattr(googleplay, 'EditService', lambda _, __, ___, commit, contact_google_play: edit_service_mock_)
    monkeypatch_.setattr('mozapkpublisher.push_apk.extract_and_check_apks_metadata', _metadata)


def test_invalid_rollout_percentage(edit_service_mock, monkeypatch):
    with pytest.raises(WrongArgumentGiven):
        # missing percentage
        push_apk(APKS, SERVICE_ACCOUNT, credentials, 'rollout', [])

    valid_percentage = 1
    invalid_track = 'production'
    with pytest.raises(WrongArgumentGiven):
        push_apk(APKS, SERVICE_ACCOUNT, credentials, invalid_track, [], rollout_percentage=valid_percentage)


def test_valid_rollout_percentage(edit_service_mock, monkeypatch):
    set_up_mocks(monkeypatch, edit_service_mock)
    valid_percentage = 50

    push_apk(APKS, SERVICE_ACCOUNT, credentials, 'rollout', [], rollout_percentage=valid_percentage)
    edit_service_mock.update_track.assert_called_once_with('rollout', ['0', '1'], valid_percentage)
    edit_service_mock.update_track.reset_mock()


def test_get_ordered_version_codes():
    assert _get_ordered_version_codes({
        'x86': {
            'version_code': '1'
        },
        'armv7_v15': {
            'version_code': '0'
        }
    }) == ['0', '1']    # should be sorted


def test_upload_apk(edit_service_mock, monkeypatch):
    set_up_mocks(monkeypatch, edit_service_mock)

    push_apk(APKS, SERVICE_ACCOUNT, credentials, 'alpha', [])

    for apk_file in (apk_arm, apk_x86):
        edit_service_mock.upload_apk.assert_any_call(apk_file.name)

    edit_service_mock.update_track.assert_called_once_with('alpha', ['0', '1'], None)
    edit_service_mock.commit_transaction.assert_called_once_with()


def test_get_distinct_package_name_apk_metadata():
    one_package_apks_metadata = {
        'fennec-1.apk': {'package_name': 'org.mozilla.firefox'},
        'fennec-2.apk': {'package_name': 'org.mozilla.firefox'}
    }

    expected_one_package_metadata = {
        'org.mozilla.firefox': {
            'fennec-1.apk': {'package_name': 'org.mozilla.firefox'},
            'fennec-2.apk': {'package_name': 'org.mozilla.firefox'}
        }
    }

    one_package_metadata = _split_apk_metadata_per_package_name(one_package_apks_metadata)
    assert len(one_package_metadata.keys()) == 1
    assert expected_one_package_metadata == one_package_metadata

    two_package_apks_metadata = {
        'focus-1.apk': {'package_name': 'org.mozilla.focus'},
        'focus-2.apk': {'package_name': 'org.mozilla.focus'},
        'klar.apk': {'package_name': 'org.mozilla.klar'}
    }

    expected_two_package_metadata = {
        'org.mozilla.klar': {
            'klar.apk': {'package_name': 'org.mozilla.klar'}
        },
        'org.mozilla.focus': {
            'focus-1.apk': {'package_name': 'org.mozilla.focus'},
            'focus-2.apk': {'package_name': 'org.mozilla.focus'}
        }
    }

    two_package_metadata = _split_apk_metadata_per_package_name(two_package_apks_metadata)
    assert len(two_package_metadata.keys()) == 2
    assert expected_two_package_metadata == two_package_metadata


def test_push_apk_tunes_down_logs(monkeypatch):
    main_logging_mock = MagicMock()
    monkeypatch.setattr('mozapkpublisher.push_apk.main_logging', main_logging_mock)
    monkeypatch.setattr('mozapkpublisher.push_apk.extract_and_check_apks_metadata', MagicMock())
    monkeypatch.setattr('mozapkpublisher.push_apk._split_apk_metadata_per_package_name', MagicMock())
    monkeypatch.setattr('mozapkpublisher.push_apk._upload_apks', MagicMock())

    push_apk(APKS, SERVICE_ACCOUNT, credentials, 'alpha', [], contact_google_play=False)

    main_logging_mock.init.assert_called_once_with()


def test_main_bad_arguments_status_code(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['script'])
    with pytest.raises(SystemExit) as exception:
        main()
    assert exception.value.code == 2


def test_main(monkeypatch):
    incomplete_args = [
        '--package-name', 'org.mozilla.fennec_aurora', '--track', 'alpha',
        '--service-account', 'foo@developer.gserviceaccount.com',
    ]

    monkeypatch.setattr(sys, 'argv', incomplete_args)

    with pytest.raises(SystemExit):
        main()

    file = os.path.join(os.path.dirname(__file__), 'data', 'blob')
    fail_manual_validation_args = [
        'script',
        '--track', 'rollout',
        '--service-account', 'foo@developer.gserviceaccount.com',
        '--credentials', file,
        '--expected-package-name', 'org.mozilla.fennec_aurora',
        file
    ]

    with patch.object(mozapkpublisher.push_apk, 'push_apk', wraps=mozapkpublisher.push_apk.push_apk) as mock_push_apk:
        monkeypatch.setattr(sys, 'argv', fail_manual_validation_args)

        with pytest.raises(SystemExit):
            main()

        assert mock_push_apk.called
