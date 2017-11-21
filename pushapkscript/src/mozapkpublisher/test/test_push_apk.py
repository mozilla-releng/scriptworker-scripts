import json
import pytest
import sys

from unittest.mock import create_autospec

from copy import copy
from tempfile import NamedTemporaryFile

from mozapkpublisher.common import apk, googleplay, store_l10n
from mozapkpublisher.common.exceptions import WrongArgumentGiven, ArmVersionCodeTooHigh
from mozapkpublisher.push_apk import PushAPK, main, _check_and_get_flatten_version_codes, \
    _create_or_update_whats_new
from mozapkpublisher.test.common.test_store_l10n import set_translations_per_google_play_locale_code, \
    DUMMY_TRANSLATIONS_PER_GOOGLE_PLAY_LOCALE


credentials = NamedTemporaryFile()
apk_x86 = NamedTemporaryFile()
apk_arm = NamedTemporaryFile()

VALID_CONFIG = {
    'package_name': 'org.mozilla.fennec_aurora',
    'track': 'alpha',
    'service-account': 'foo@developer.gserviceaccount.com',
    'credentials': credentials.name,
    'apk_x86': apk_x86.name,
    'apk_armv7_v15': apk_arm.name,
    'update_gp_strings_from_l10n_store': True,
    'commit': False,
    'do_not_contact_google_play': False,
}


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
    monkeypatch_.setattr(googleplay, 'EditService', lambda _, __, ___, commit, contact_google_play: edit_service_mock_)
    monkeypatch_.setattr(apk, 'check_if_apk_is_multilocale', lambda _: None)
    monkeypatch_.setattr(apk, 'check_if_apk_has_claimed_architecture', lambda _, __: None)
    set_translations_per_google_play_locale_code(monkeypatch_)


def test_one_missing_file():
    config = copy(VALID_CONFIG)

    for field in ('credentials', 'apk_x86', 'apk_armv7_v15'):
        old_value = config[field]

        del config[field]
        with pytest.raises(WrongArgumentGiven):
            PushAPK(config)

        config[field] = old_value


def test_tracks():
    config = copy(VALID_CONFIG)
    config['track'] = 'fake'

    with pytest.raises(WrongArgumentGiven):
        PushAPK(config)

    for track in ('alpha', 'beta', 'production'):
        config['track'] = track
        PushAPK(config)


def test_invalid_rollout_percentage(edit_service_mock, monkeypatch):
    config = copy(VALID_CONFIG)
    config['track'] = 'rollout'

    with pytest.raises(WrongArgumentGiven):
        # missing percentage
        PushAPK(config)

    for invalid_percentage in (-1, 0.5, 101):
        config['rollout_percentage'] = invalid_percentage
        with pytest.raises(WrongArgumentGiven):
            PushAPK(config)

    valid_percentage = 1
    invalid_track = 'production'
    config['rollout_percentage'] = valid_percentage
    config['track'] = invalid_track
    with pytest.raises(WrongArgumentGiven):
        PushAPK(config)


def test_valid_rollout_percentage(edit_service_mock, monkeypatch):
    config = copy(VALID_CONFIG)
    config['track'] = 'rollout'

    set_up_mocks(monkeypatch, edit_service_mock)
    for i in range(0, 101):
        valid_percentage = i
        config['rollout_percentage'] = valid_percentage

        PushAPK(config).run()
        edit_service_mock.update_track.assert_called_once_with('rollout', ['0', '1'], valid_percentage)
        edit_service_mock.update_track.reset_mock()


def test_check_and_get_flatten_version_codes():
    assert _check_and_get_flatten_version_codes({
        'x86': {
            'version_code': '1'
        },
        'armv7_v15': {
            'version_code': '0'
        }
    }) == ['0', '1']    # should be sorted

    with pytest.raises(ArmVersionCodeTooHigh):
        _check_and_get_flatten_version_codes({
            'x86': {
                'version_code': '0'
            },
            'armv7_v15': {
                'version_code': '1'
            }
        })


def test_upload_apk(edit_service_mock, monkeypatch):
    set_up_mocks(monkeypatch, edit_service_mock)

    PushAPK(VALID_CONFIG).run()

    for apk_file in (apk_arm, apk_x86):
        edit_service_mock.upload_apk.assert_any_call(apk_file.name)

    edit_service_mock.update_track.assert_called_once_with('alpha', ['0', '1'], None)
    edit_service_mock.commit_transaction.assert_called_once_with()


def test_upload_apk_with_locales_updated_from_l10n_store(edit_service_mock, monkeypatch):
    set_up_mocks(monkeypatch, edit_service_mock)
    monkeypatch.setattr(store_l10n, '_translate_moz_locate_into_google_play_one', lambda locale: 'es-US' if locale == 'es-MX' else locale)

    config = copy(VALID_CONFIG)
    config['package_name'] = 'org.mozilla.firefox_beta'
    PushAPK(config).run()

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

    config = copy(VALID_CONFIG)
    del config['update_gp_strings_from_l10n_store']
    config['no_gp_string_update'] = True
    PushAPK(config).run()

    assert edit_service_mock.upload_apk.call_count == 2
    assert edit_service_mock.update_track.call_count == 1
    assert edit_service_mock.commit_transaction.call_count == 1

    assert edit_service_mock.update_listings.call_count == 0
    assert edit_service_mock.update_whats_new.call_count == 0


def test_upload_apk_with_locales_updated_from_file(edit_service_mock, monkeypatch):
    set_up_mocks(monkeypatch, edit_service_mock)

    config = copy(VALID_CONFIG)
    del config['update_gp_strings_from_l10n_store']

    with NamedTemporaryFile('w') as f:
        json.dump(DUMMY_TRANSLATIONS_PER_GOOGLE_PLAY_LOCALE, f)
        f.seek(0)
        config['update_gp_strings_from_file'] = f.name
        PushAPK(config).run()

    assert edit_service_mock.upload_apk.call_count == 2
    assert edit_service_mock.update_track.call_count == 1
    assert edit_service_mock.commit_transaction.call_count == 1

    assert edit_service_mock.update_listings.call_count == 3


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
    monkeypatch.setattr(apk, 'check_if_apk_is_multilocale', lambda _: None)
    monkeypatch.setattr(apk, 'check_if_apk_has_claimed_architecture', lambda _, __: None)
    set_translations_per_google_play_locale_code(monkeypatch)

    config = copy(VALID_CONFIG)
    config['do_not_contact_google_play'] = True

    PushAPK(config).run()
    # Checks are done by the fact that Google Play doesn't error out. In fact, we
    # provide dummy data. If Google Play was reached, it would have failed at the
    # authentication step


def test_main(monkeypatch):
    incomplete_args = [
        '--package-name', 'org.mozilla.fennec_aurora', '--track', 'alpha',
        '--service-account', 'foo@developer.gserviceaccount.com',
    ]

    monkeypatch.setattr(sys, 'argv', incomplete_args)

    with pytest.raises(SystemExit):
        main()
