import pytest
import sys

from copy import copy
from tempfile import NamedTemporaryFile

from mozapkpublisher import store_l10n, apk
from mozapkpublisher.exceptions import WrongArgumentGiven
from mozapkpublisher.push_apk import PushAPK, main

from mozapkpublisher.test.helpers import craft_service_mock


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


def test_rollout_percentage(monkeypatch):
    config = copy(VALID_CONFIG)
    config['track'] = 'rollout'

    with pytest.raises(WrongArgumentGiven):
        PushAPK(config)

    for invalid_percentage in (-1, 0.5, 101):
        config['rollout_percentage'] = invalid_percentage
        with pytest.raises(WrongArgumentGiven):
            PushAPK(config)

    edit_service_mock = craft_service_mock(monkeypatch)
    monkeypatch.setattr(apk, 'check_if_apk_is_multilocale', lambda _: None)
    for i in range(0, 101):
        valid_percentage = i
        config['rollout_percentage'] = valid_percentage

        PushAPK(config).run()
        edit_service_mock.update_track.assert_called_once_with('rollout', {
            u'versionCodes': [str(2*i), str(2*i+1)],    # Doesn't provide much value to test, only here to fill gaps
            u'userFraction': valid_percentage / 100.0   # Ensure float in Python 2
        })
        edit_service_mock.update_track.reset_mock()


def test_upload_apk(monkeypatch):
    edit_service_mock = craft_service_mock(monkeypatch)
    monkeypatch.setattr(apk, 'check_if_apk_is_multilocale', lambda _: None)

    PushAPK(VALID_CONFIG).run()

    for apk_file in (apk_arm, apk_x86):
        edit_service_mock.upload_apk.assert_any_call(apk_file.name)

    edit_service_mock.update_track.assert_called_once_with('alpha', {u'versionCodes': ['0', '1']})
    edit_service_mock.commit_transaction.assert_called_once_with()


def test_upload_apk_with_whats_new(monkeypatch):
    edit_service_mock = craft_service_mock(monkeypatch)
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
        # Unlike what we could infer from the data input, en-GB is NOT converted into en-US.
        # en-GB is not meant to be updated and en-US is added to list_locales
        ('en-US', 'Check out this cool feature!'),
    )

    for (locale, whats_new) in expected_locales:
        for version_code in range(2):
            edit_service_mock.update_apk_listings.assert_any_call(locale, str(version_code), body={
                'recentChanges': whats_new
            })

    assert edit_service_mock.update_apk_listings.call_count == 4
    edit_service_mock.commit_transaction.assert_called_once_with()


def test_main(monkeypatch):
    incomplete_args = [
        '--package-name', 'org.mozilla.fennec_aurora', '--track', 'alpha',
        '--service-account', 'foo@developer.gserviceaccount.com',
    ]

    monkeypatch.setattr(sys, 'argv', incomplete_args)

    with pytest.raises(SystemExit):
        main()
