import pytest
import sys

from copy import copy
from tempfile import NamedTemporaryFile

from mozapkpublisher import store_l10n
from mozapkpublisher.exceptions import WrongArgumentGiven
from mozapkpublisher.update_apk_description import UpdateDescriptionAPK, main

from mozapkpublisher.test.helpers import craft_service_mock

credentials = NamedTemporaryFile()

VALID_CONFIG = {
    'package_name': 'org.mozilla.firefox_beta',
    'service-account': 'foo@developer.gserviceaccount.com',
    'credentials': credentials.name,
}


def test_aurora_not_supported():
    config = copy(VALID_CONFIG)
    config['package_name'] = 'org.mozilla.fennec_aurora'

    with pytest.raises(WrongArgumentGiven):
        UpdateDescriptionAPK(config)


def test_update_apk_description_force_locale(monkeypatch):
    edit_service_mock = craft_service_mock(monkeypatch)
    monkeypatch.setattr(store_l10n, 'get_translation', lambda _, locale: {
        'title': 'Firefox for Android',
        'long_desc': 'Long description',
        'short_desc': 'Short',
        'whatsnew': 'Check out this cool feature!',
    } if locale == 'en-US' else None)
    monkeypatch.setattr(store_l10n, 'locale_mapping', lambda locale: 'google_play_locale')

    config = copy(VALID_CONFIG)
    config['force_locale'] = 'en-US'
    UpdateDescriptionAPK(config).run()

    edit_service_mock.update_listings.assert_called_once_with('google_play_locale', body={
        'fullDescription': 'Long description',
        'shortDescription': 'Short',
        'title': 'Firefox for Android',
    })

    assert edit_service_mock.update_listings.call_count == 1
    edit_service_mock.commit_transaction.assert_called_once_with()


def test_main(monkeypatch):
    incomplete_args = [
        '--package-name', 'org.mozilla.firefox_beta',
        '--service-account', 'foo@developer.gserviceaccount.com',
    ]

    monkeypatch.setattr(sys, 'argv', incomplete_args)

    with pytest.raises(SystemExit):
        main()
