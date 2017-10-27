import pytest

from unittest.mock import MagicMock

from mozapkpublisher.common import store_l10n, utils
from mozapkpublisher.common.exceptions import NoTranslationGiven, TranslationMissingData
from mozapkpublisher.common.store_l10n import get_translations_per_google_play_locale_code, \
    check_translations_schema, _get_list_of_completed_locales, _get_translation, \
    _translate_moz_locate_into_google_play_one

DUMMY_TRANSLATIONS_PER_GOOGLE_PLAY_LOCALE = {
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


def set_translations_per_google_play_locale_code(_monkeypatch):
    _monkeypatch.setattr(store_l10n, '_translations_per_google_play_locale_code', DUMMY_TRANSLATIONS_PER_GOOGLE_PLAY_LOCALE)


def test_get_translations_per_google_play_locale_code(monkeypatch):
    set_translations_per_google_play_locale_code(monkeypatch)
    monkeypatch.setattr(store_l10n, '_mappings', {
        'es-MX': 'es-US',
    })

    assert get_translations_per_google_play_locale_code('org.mozilla.firefox_beta') == {
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

    assert get_translations_per_google_play_locale_code('org.mozilla.firefox', moz_locales=['es-MX']) == {
        'es-US': {
            'title': 'Navegador web Firefox',
            'long_desc': 'Descripcion larga',
            'short_desc': 'Corto',
            'whatsnew': 'Mire a esta caracteristica',
        },
    }


@pytest.mark.parametrize('translations', (
    DUMMY_TRANSLATIONS_PER_GOOGLE_PLAY_LOCALE,
    {'en-US': {'long_desc': 'missing whatsnew', 'short_desc': 'no whatsnew', 'title': 'No whastnew'}},
))
def test_check_translations_schema(translations):
    check_translations_schema(translations)


@pytest.mark.parametrize('translations, exception', (
    ({}, NoTranslationGiven),
    ([{'long_desc': 'not a dict', 'name': 'en-US', 'short_desc': 'not dict', 'title': 'Not Dict'}], AttributeError),
    ({'en-US': {'short_desc': 'no long_desc', 'title': 'No Long Desc'}}, TranslationMissingData),
    ({'en-US': {'long_desc': 'missing short_desc', 'title': 'No Short Desc'}}, TranslationMissingData),
    ({'en-US': {'long_desc': 'missing title', 'short_desc': 'no title'}}, TranslationMissingData),
))
def test_bad_check_translations_schema(translations, exception):
    with pytest.raises(exception):
        check_translations_schema(translations)


def test_get_list_of_completed_locales(monkeypatch):
    monkeypatch.setattr(
        utils, 'load_json_url',
        lambda url: [u'en-GB', u'es-ES']
        if url == 'https://l10n.mozilla-community.org/stores_l10n/api/v1/fx_android/listing/beta/' else None
    )
    assert _get_list_of_completed_locales('fx_android', 'beta') == [u'en-GB', u'es-ES']


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
    assert _get_translation('fx_android', 'beta', 'en-GB') == {
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
