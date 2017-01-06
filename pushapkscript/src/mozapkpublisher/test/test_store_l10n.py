try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

from mozapkpublisher import utils

from mozapkpublisher.store_l10n import get_list_locales, get_translation, locale_mapping

L10N_API_URL = 'https://l10n.mozilla-community.org/stores_l10n/'
ALL_LOCALES_URL = L10N_API_URL + 'api/v1/fx_android/listing/{channel}/'
LOCALE_URL = L10N_API_URL + 'api/v1/fx_android/translation/{channel}/{locale}/'
MAPPING_URL = L10N_API_URL + 'api/v1/google/localesmapping/?reverse'

_mappings = None


def test_get_list_locales(monkeypatch):
    monkeypatch.setattr(
        utils, 'load_json_url',
        lambda url: [u'en-GB', u'es-ES']
        if url == 'https://l10n.mozilla-community.org/stores_l10n/api/v1/fx_android/listing/beta/' else None
    )
    assert get_list_locales('beta') == [u'en-GB', u'es-ES']


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
    assert get_translation('beta', 'en-GB') == {
        'title': 'Firefox for Android Beta',
        'long_desc': 'Long description',
        'short_desc': 'Short',
        'whatsnew': 'Check out this cool feature!',
    }


def test_locale_mapping(monkeypatch):
    mock_json_url = MagicMock()
    mock_json_url.side_effect = lambda url: {
        u'en-GB': u'en-GB',
        u'es-MX': u'es-US',
    } if url == 'https://l10n.mozilla-community.org/stores_l10n/api/v1/google/localesmapping/?reverse' else None

    monkeypatch.setattr(utils, 'load_json_url', mock_json_url)
    assert locale_mapping('en-GB') == 'en-GB'
    assert locale_mapping('es-MX') == 'es-US'
    assert mock_json_url.call_count == 1
    assert locale_mapping('non-mapped-locale') == 'non-mapped-locale'
