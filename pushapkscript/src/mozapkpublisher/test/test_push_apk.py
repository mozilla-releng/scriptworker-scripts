from contextlib import contextmanager

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
def google_play_edit_mock():
    return create_autospec(googleplay.GooglePlayEdit)


def set_up_mocks(monkeypatch_, google_play_edit_mock_):
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

    @contextmanager
    def fake_edit(_, __, ___, *, contact_google_play, commit):
        yield google_play_edit_mock_

    monkeypatch_.setattr(googleplay, 'edit', fake_edit)
    monkeypatch_.setattr('mozapkpublisher.push_apk.extract_and_check_apks_metadata', _metadata)


def test_rollout_without_rollout_percentage():
    # Note: specifying "track='rollout'" (even with a valid percentage) is currently deprecated

    with pytest.raises(WrongArgumentGiven):
        # using the track "rollout" without a percentage
        push_apk(APKS, SERVICE_ACCOUNT, credentials, 'rollout', [])


def test_valid_rollout_percentage_with_track_rollout(google_play_edit_mock, monkeypatch):
    set_up_mocks(monkeypatch, google_play_edit_mock)
    valid_percentage = 50

    push_apk(APKS, SERVICE_ACCOUNT, credentials, 'rollout', [], rollout_percentage=valid_percentage, contact_google_play=False)
    google_play_edit_mock.update_track.assert_called_once_with('production', ['0', '1'], valid_percentage)
    google_play_edit_mock.update_track.reset_mock()


def test_valid_rollout_percentage_with_real_track(google_play_edit_mock, monkeypatch):
    set_up_mocks(monkeypatch, google_play_edit_mock)
    valid_percentage = 50

    push_apk(APKS, SERVICE_ACCOUNT, credentials, 'beta', [], rollout_percentage=valid_percentage, contact_google_play=False)
    google_play_edit_mock.update_track.assert_called_once_with('beta', ['0', '1'], valid_percentage)
    google_play_edit_mock.update_track.reset_mock()


def test_get_ordered_version_codes():
    assert _get_ordered_version_codes({
        'x86': {
            'version_code': '1'
        },
        'armv7_v15': {
            'version_code': '0'
        }
    }) == ['0', '1']    # should be sorted


def test_upload_apk(google_play_edit_mock, monkeypatch):
    set_up_mocks(monkeypatch, google_play_edit_mock)

    push_apk(APKS, SERVICE_ACCOUNT, credentials, 'alpha', [], contact_google_play=False)

    for apk_file in (apk_arm, apk_x86):
        google_play_edit_mock.upload_apk.assert_any_call(apk_file.name)

    google_play_edit_mock.update_track.assert_called_once_with('alpha', ['0', '1'], None)


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
