import json
import mozapkpublisher
import os
import pytest
import sys

from unittest.mock import create_autospec

from tempfile import NamedTemporaryFile

from mozapkpublisher.common import googleplay, store_l10n
from mozapkpublisher.common.apk import checker, extractor
from mozapkpublisher.common.exceptions import WrongArgumentGiven
from mozapkpublisher.push_apk import push_apk, main, _create_or_update_whats_new, \
    _get_ordered_version_codes, _split_apk_metadata_per_package_name, StoreGooglePlayStrings, FileGooglePlayStrings
from mozapkpublisher.test.common.test_store_l10n import set_translations_per_google_play_locale_code, \
    DUMMY_TRANSLATIONS_PER_GOOGLE_PLAY_LOCALE
from unittest.mock import patch


credentials = NamedTemporaryFile()
apk_x86 = NamedTemporaryFile()
apk_arm = NamedTemporaryFile()

APKS = [apk_x86, apk_arm]
SERVICE_ACCOUNT = 'foo@developer.gserviceaccount.com'


@pytest.fixture
def edit_service_mock():
    _edit_service_mock = create_autospec(googleplay.EditService)

    def _generate_version_code(apk_file_name):
        if apk_file_name == apk_arm.name:
            version_code = 0
        elif apk_file_name == apk_x86.name:
            version_code = 1
        else:
            raise Exception('Unsupported APK')

        return {'versionCode': str(version_code)}

    _edit_service_mock.upload_apk.side_effect = _generate_version_code
    return _edit_service_mock


def set_up_mocks(monkeypatch_, edit_service_mock_):
    def _metadata(apk_file_name):
        if apk_file_name == apk_arm.name:
            version_code = '0'
            architecture = 'armeabi-v7a'
        elif apk_file_name == apk_x86.name:
            version_code = '1'
            architecture = 'x86'

        return {
            'architecture': architecture,
            'firefox_build_id': '20171112125738',
            'version_code': version_code,
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
            'firefox_version': '57.0'
        }

    monkeypatch_.setattr(googleplay, 'EditService', lambda _, __, ___, commit, contact_google_play: edit_service_mock_)
    monkeypatch_.setattr(extractor, 'extract_metadata', _metadata)
    monkeypatch_.setattr(checker, 'cross_check_apks', lambda _: None)
    set_translations_per_google_play_locale_code(monkeypatch_)


def test_tracks(edit_service_mock, monkeypatch):
    set_up_mocks(monkeypatch, edit_service_mock)

    with pytest.raises(WrongArgumentGiven):
        push_apk(APKS, SERVICE_ACCOUNT, credentials, 'fake')

    for track in ('alpha', 'beta', 'production'):
        push_apk(APKS, SERVICE_ACCOUNT, credentials, track)


def test_invalid_rollout_percentage(edit_service_mock, monkeypatch):
    with pytest.raises(WrongArgumentGiven):
        # missing percentage
        push_apk(APKS, SERVICE_ACCOUNT, credentials, 'rollout')

    valid_percentage = 1
    invalid_track = 'production'
    with pytest.raises(WrongArgumentGiven):
        push_apk(APKS, SERVICE_ACCOUNT, credentials, invalid_track, rollout_percentage=valid_percentage)


def test_valid_rollout_percentage(edit_service_mock, monkeypatch):
    set_up_mocks(monkeypatch, edit_service_mock)
    valid_percentage = 50

    push_apk(APKS, SERVICE_ACCOUNT, credentials, 'rollout', rollout_percentage=valid_percentage)
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

    push_apk(APKS, SERVICE_ACCOUNT, credentials, 'alpha')

    for apk_file in (apk_arm, apk_x86):
        edit_service_mock.upload_apk.assert_any_call(apk_file.name)

    edit_service_mock.update_track.assert_called_once_with('alpha', ['0', '1'], None)
    edit_service_mock.commit_transaction.assert_called_once_with()


def test_upload_apk_with_locales_updated_from_l10n_store(edit_service_mock, monkeypatch):
    set_up_mocks(monkeypatch, edit_service_mock)
    monkeypatch.setattr(store_l10n, '_translate_moz_locate_into_google_play_one', lambda locale: 'es-US' if locale == 'es-MX' else locale)

    push_apk(APKS, SERVICE_ACCOUNT, credentials, 'alpha', google_play_strings=StoreGooglePlayStrings())

    expected_locales = (
        ('es-US', 'Navegador web Firefox', 'Corto', 'Descripcion larga', 'Mire a esta caracteristica'),
        ('en-GB', 'Firefox for Android', 'Short', 'Long description', 'Check out this cool feature!'),
        ('en-US', 'Firefox for Android', 'Short', 'Long description', 'Check out this cool feature!'),
    )

    for (locale, title, short_description, full_description, whats_new) in expected_locales:
        edit_service_mock.update_listings.assert_any_call(
            locale, full_description=full_description, short_description=short_description, title=title
        )

        for version_code in range(2):
            edit_service_mock.update_whats_new.assert_any_call(locale, str(version_code), whats_new=whats_new)

    assert edit_service_mock.update_listings.call_count == 3
    assert edit_service_mock.update_whats_new.call_count == 6
    edit_service_mock.commit_transaction.assert_called_once_with()


def test_upload_apk_without_locales_updated(edit_service_mock, monkeypatch):
    set_up_mocks(monkeypatch, edit_service_mock)

    push_apk(APKS, SERVICE_ACCOUNT, credentials, 'alpha')

    assert edit_service_mock.upload_apk.call_count == 2
    assert edit_service_mock.update_track.call_count == 1
    assert edit_service_mock.commit_transaction.call_count == 1

    assert edit_service_mock.update_listings.call_count == 0
    assert edit_service_mock.update_whats_new.call_count == 0


def test_upload_apk_with_locales_updated_from_file(edit_service_mock, monkeypatch):
    set_up_mocks(monkeypatch, edit_service_mock)

    with NamedTemporaryFile('r+') as f:
        json.dump(DUMMY_TRANSLATIONS_PER_GOOGLE_PLAY_LOCALE, f)
        f.seek(0)
        push_apk(APKS, SERVICE_ACCOUNT, credentials, 'alpha', google_play_strings=FileGooglePlayStrings(f))

    assert edit_service_mock.upload_apk.call_count == 2
    assert edit_service_mock.update_track.call_count == 1
    assert edit_service_mock.commit_transaction.call_count == 1

    assert edit_service_mock.update_listings.call_count == 3


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


def test_create_or_update_whats_new(edit_service_mock, monkeypatch):
    # Don't update Nightly
    _create_or_update_whats_new(
        edit_service_mock, 'org.mozilla.fennec_aurora', '1',
        DUMMY_TRANSLATIONS_PER_GOOGLE_PLAY_LOCALE
    )
    assert edit_service_mock.update_whats_new.call_count == 0

    # Update anything else than nightly
    _create_or_update_whats_new(
        edit_service_mock, 'org.mozilla.firefox_beta', '1',
        DUMMY_TRANSLATIONS_PER_GOOGLE_PLAY_LOCALE
    )
    assert edit_service_mock.update_whats_new.call_count == 3


def test_do_not_contact_google_play_flag_does_not_request_google_play(monkeypatch):
    monkeypatch.setattr(extractor, 'extract_metadata', lambda _: {
        'package_name': 'org.mozilla.firefox',
        'version_code': '1',
    })
    monkeypatch.setattr(checker, 'cross_check_apks', lambda _: None)
    set_translations_per_google_play_locale_code(monkeypatch)

    push_apk(APKS, SERVICE_ACCOUNT, credentials, 'alpha', contact_google_play=False)
    # Checks are done by the fact that Google Play doesn't error out. In fact, we
    # provide dummy data. If Google Play was reached, it would have failed at the
    # authentication step


def test_custom_google_play_track(edit_service_mock, monkeypatch):
    set_up_mocks(monkeypatch, edit_service_mock)

    monkeypatch.setattr(extractor, 'extract_metadata', lambda _: {
        'package_name': 'org.mozilla.firefox',
        'version_code': '1',
    })

    # No "nightly" google play track for Firefox
    with pytest.raises(WrongArgumentGiven):
        push_apk(APKS, SERVICE_ACCOUNT, credentials, 'nightly')

    # "nightly" track is an allowed value for Focus
    monkeypatch.setattr(extractor, 'extract_metadata', lambda _: {
        'package_name': 'org.mozilla.focus',
        'version_code': '1',
    })

    push_apk(APKS, SERVICE_ACCOUNT, credentials, 'nightly')


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
        '--no-gp-string-update',
        file
    ]

    with patch.object(mozapkpublisher.push_apk, 'push_apk', wraps=mozapkpublisher.push_apk.push_apk) as mock_push_apk:
        monkeypatch.setattr(sys, 'argv', fail_manual_validation_args)

        with pytest.raises(SystemExit):
            main()

        assert mock_push_apk.called
