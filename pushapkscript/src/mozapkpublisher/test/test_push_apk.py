import pytest
import sys

try:
    from unittest.mock import create_autospec
except ImportError:
    from mock import create_autospec

from copy import copy
from tempfile import NamedTemporaryFile

from mozapkpublisher import apk, googleplay, store_l10n
from mozapkpublisher.exceptions import WrongArgumentGiven, ArmVersionCodeTooHigh
from mozapkpublisher.push_apk import PushAPK, main, _check_and_get_flatten_version_codes


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


def test_rollout_percentage(edit_service_mock, monkeypatch):
    config = copy(VALID_CONFIG)
    config['track'] = 'rollout'

    with pytest.raises(WrongArgumentGiven):
        PushAPK(config)

    for invalid_percentage in (-1, 0.5, 101):
        config['rollout_percentage'] = invalid_percentage
        with pytest.raises(WrongArgumentGiven):
            PushAPK(config)

    monkeypatch.setattr(googleplay, 'EditService', lambda _, __, ___, ____: edit_service_mock)
    monkeypatch.setattr(apk, 'check_if_apk_is_multilocale', lambda _: None)
    for i in range(0, 101):
        valid_percentage = i
        config['rollout_percentage'] = valid_percentage

        PushAPK(config).run()
        edit_service_mock.update_track.assert_called_once_with('rollout', {
            u'versionCodes': ['0', '1'],
            u'userFraction': valid_percentage / 100.0   # Ensure float in Python 2
        })
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
    monkeypatch.setattr(googleplay, 'EditService', lambda _, __, ___, ____: edit_service_mock)
    monkeypatch.setattr(apk, 'check_if_apk_is_multilocale', lambda _: None)

    PushAPK(VALID_CONFIG).run()

    for apk_file in (apk_arm, apk_x86):
        edit_service_mock.upload_apk.assert_any_call(apk_file.name)

    edit_service_mock.update_track.assert_called_once_with('alpha', {u'versionCodes': ['0', '1']})
    edit_service_mock.commit_transaction.assert_called_once_with()


def test_upload_apk_with_whats_new(edit_service_mock, monkeypatch):
    monkeypatch.setattr(googleplay, 'EditService', lambda _, __, ___, ____: edit_service_mock)
    monkeypatch.setattr(apk, 'check_if_apk_is_multilocale', lambda _: None)

    monkeypatch.setattr(store_l10n, 'get_list_locales', lambda _: [u'en-GB', u'es-MX'])
    monkeypatch.setattr(store_l10n, 'get_translation', lambda _, locale: {
        'title': 'Navegador web Firefox',
        'long_desc': 'descripcion larga',
        'short_desc': 'corto',
        'whatsnew': 'Mire a esta caracteristica',
    } if locale == 'es-MX' else {
        'title': 'Firefox for Android',
        'long_desc': 'Long description',
        'short_desc': 'Short',
        'whatsnew': 'Check out this cool feature!',
    })
    monkeypatch.setattr(store_l10n, 'locale_mapping', lambda locale: 'es-US' if locale == 'es-MX' else locale)

    config = copy(VALID_CONFIG)
    config['package_name'] = 'org.mozilla.firefox_beta'
    PushAPK(config).run()

    expected_locales = (
        ('es-US', 'Mire a esta caracteristica'),
        ('en-GB', 'Check out this cool feature!'),
        ('en-US', 'Check out this cool feature!'),
    )

    for (locale, whats_new) in expected_locales:
        for version_code in range(2):
            edit_service_mock.update_apk_listings.assert_any_call(locale, str(version_code), body={
                'recentChanges': whats_new
            })

    assert edit_service_mock.update_apk_listings.call_count == 6
    edit_service_mock.commit_transaction.assert_called_once_with()


def test_main(monkeypatch):
    incomplete_args = [
        '--package-name', 'org.mozilla.fennec_aurora', '--track', 'alpha',
        '--service-account', 'foo@developer.gserviceaccount.com',
    ]

    monkeypatch.setattr(sys, 'argv', incomplete_args)

    with pytest.raises(SystemExit):
        main()
