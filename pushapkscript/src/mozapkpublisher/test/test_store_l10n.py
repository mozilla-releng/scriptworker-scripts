try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

from mozapkpublisher import utils

from mozapkpublisher import store_l10n
from mozapkpublisher.store_l10n import get_translations_per_google_play_locale_code, \
    _get_list_of_completed_locales, _get_translation, _translate_moz_locate_into_google_play_one

L10N_API_URL = 'https://l10n.mozilla-community.org/stores_l10n/'
ALL_LOCALES_URL = L10N_API_URL + 'api/v1/fx_android/listing/{channel}/'
LOCALE_URL = L10N_API_URL + 'api/v1/fx_android/translation/{channel}/{locale}/'
MAPPING_URL = L10N_API_URL + 'api/v1/google/localesmapping/?reverse'

_mappings = None


def set_translations_per_google_play_locale_code(_monkeypatch):
    _monkeypatch.setattr(store_l10n, '_translations_per_google_play_locale_code', {
        'en-GB': {
            'title': 'Firefox for Android',
            'long_desc': 'Long description',
            'short_desc': 'Short',
            'whatsnew': 'Check out this cool feature!',
        },
        'en-US': {
            'title': 'Firefox for Android',
            'long_desc': 'Long description',
            'short_desc': 'Short',
            'whatsnew': 'Check out this cool feature!',
        },
        'es-US': {
            'title': 'Navegador web Firefox',
            'long_desc': 'Descripcion larga',
            'short_desc': 'Corto',
            'whatsnew': 'Mire a esta caracteristica',
        },
    })


def test_get_translations_per_google_play_locale_code(monkeypatch):
    set_translations_per_google_play_locale_code(monkeypatch)
    monkeypatch.setattr(store_l10n, '_mappings', {
        'es-MX': 'es-US',
    })

    assert get_translations_per_google_play_locale_code('beta') == {
        'en-GB': {
            'title': 'Firefox for Android',
            'long_desc': 'Long description',
            'short_desc': 'Short',
            'whatsnew': 'Check out this cool feature!',
        },
        'en-US': {
            'title': 'Firefox for Android',
            'long_desc': 'Long description',
            'short_desc': 'Short',
            'whatsnew': 'Check out this cool feature!',
        },
        'es-US': {
            'title': 'Navegador web Firefox',
            'long_desc': 'Descripcion larga',
            'short_desc': 'Corto',
            'whatsnew': 'Mire a esta caracteristica',
        },
    }

    assert get_translations_per_google_play_locale_code('release', moz_locales=['es-MX']) == {
        'es-US': {
            'title': 'Navegador web Firefox',
            'long_desc': 'Descripcion larga',
            'short_desc': 'Corto',
            'whatsnew': 'Mire a esta caracteristica',
        },
    }


def test_get_list_of_completed_locales(monkeypatch):
    monkeypatch.setattr(
        utils, 'load_json_url',
        lambda url: [u'en-GB', u'es-ES']
        if url == 'https://l10n.mozilla-community.org/stores_l10n/api/v1/fx_android/listing/beta/' else None
    )
    assert _get_list_of_completed_locales('beta') == [u'en-GB', u'es-ES']


def test_get_translation(monkeypatch):
    monkeypatch.setattr(
        utils, 'load_json_url',
        lambda url: {
            'title': 'Firefox for Android Beta',
            'long_desc': 'Long description',
            'short_desc': 'Short',
            'whatsnew': 'Check out this cool feature!'
        } if url == 'https://l10n.mozilla-community.org/stores_l10n/api/v1/fx_android/translation/beta/en-GB/' else None
    )
    assert _get_translation('beta', 'en-GB') == {
        'title': 'Firefox for Android Beta',
        'long_desc': 'Long description',
        'short_desc': 'Short',
        'whatsnew': 'Check out this cool feature!',
    }


def test_translate_moz_locate_into_google_play_one(monkeypatch):
    mock_json_url = MagicMock()
    mock_json_url.side_effect = lambda url: {
        u'en-GB': u'en-GB',
        u'es-MX': u'es-US',
    } if url == 'https://l10n.mozilla-community.org/stores_l10n/api/v1/google/localesmapping/?reverse' else None

    monkeypatch.setattr(utils, 'load_json_url', mock_json_url)
    # Makes sure the locale mappings hasn't been loaded yet
    monkeypatch.setattr(store_l10n, '_mappings', None)
    assert _translate_moz_locate_into_google_play_one('en-GB') == 'en-GB'
    assert _translate_moz_locate_into_google_play_one('es-MX') == 'es-US'

    # Mappings should be loaded only once
    assert mock_json_url.call_count == 1
    assert _translate_moz_locate_into_google_play_one('non-mapped-locale') == 'non-mapped-locale'
