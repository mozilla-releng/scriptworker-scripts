import logging

from voluptuous import Schema, Required, Optional, MultipleInvalid

from mozapkpublisher.common import utils
from mozapkpublisher.common.exceptions import NoTranslationGiven, TranslationMissingData

logger = logging.getLogger(__name__)

STORE_PRODUCT_DETAILS_PER_PACKAGE_NAME = {
    'org.mozilla.fennec_aurora': {
        'product': 'fx_android',
        # Due to project Dawn, Nightly is now using the Aurora package name.
        # See https://bugzilla.mozilla.org/show_bug.cgi?id=1357351
        'channel': 'nightly',
    },
    'org.mozilla.firefox_beta': {
        'product': 'fx_android',
        'channel': 'beta',
    },
    'org.mozilla.firefox': {
        'product': 'fx_android',
        'channel': 'release',
    },
    'org.mozilla.focus': {
        'product': 'focus_android',
        'channel': 'release',
    },
    'org.mozilla.klar': {
        'product': 'klar_android',
        'channel': 'release',
    }
}

# API documentation: https://l10n.mozilla-community.org/stores_l10n/documentation/
L10N_API_URL = 'https://l10n.mozilla-community.org/stores_l10n/api/v1'
_ALL_LOCALES_URL = L10N_API_URL + '/{product}/listing/{channel}/'
_LOCALE_URL = L10N_API_URL + '/{product}/translation/{channel}/{locale}/'
_MAPPING_URL = L10N_API_URL + '/google/localesmapping/?reverse'

# Because these scripts are meant to run and exit, we cache the stores_l10n results
# in these globals
_translations_per_google_play_locale_code = None
_mappings = None

TRANSLATION_SCHEMA = Schema({
    Required('long_desc'): str,
    Required('short_desc'): str,
    Required('title'): str,
    Optional('whatsnew'): str,
})


def get_translations_per_google_play_locale_code(package_name, moz_locales=None):
    product_details = STORE_PRODUCT_DETAILS_PER_PACKAGE_NAME[package_name]
    product = product_details['product']
    channel = product_details['channel']

    global _translations_per_google_play_locale_code

    _init_full_locales_if_needed(product, channel)

    translations = _translations_per_google_play_locale_code if moz_locales is None else {
        _translate_moz_locate_into_google_play_one(moz_locale):
        _translations_per_google_play_locale_code[
            _translate_moz_locate_into_google_play_one(moz_locale)
        ]
        for moz_locale in moz_locales
    }

    check_translations_schema(translations)
    return translations


def check_translations_schema(translations):
    if not translations:
        raise NoTranslationGiven(translations)

    for locale, translation in translations.items():
        try:
            TRANSLATION_SCHEMA(translation)
        except MultipleInvalid as e:
            raise TranslationMissingData(locale, e)


def _init_full_locales_if_needed(product, channel):
    global _translations_per_google_play_locale_code

    if _translations_per_google_play_locale_code is None:
        moz_locales = _get_list_of_completed_locales(product, channel)
        moz_locales.append(u'en-US')

        logger.info('Downloading {} locales: {}...'.format(
            len(moz_locales), moz_locales
        ))
        _translations_per_google_play_locale_code = {
            _translate_moz_locate_into_google_play_one(moz_locale):
            _get_translation(product, channel, moz_locale)
            for moz_locale in moz_locales
        }
        logger.info('Locales downloaded and converted to: {}'.format(
            _translations_per_google_play_locale_code.keys()
        ))


def _get_list_of_completed_locales(product, channel):
    """ Get all the translated locales supported by Google play
    So, locale unsupported by Google play won't be downloaded
    Idem for not translated locale
    """
    return utils.load_json_url(_ALL_LOCALES_URL.format(product=product, channel=channel))


def _get_translation(product, channel, locale):
    return utils.load_json_url(_LOCALE_URL.format(product=product, channel=channel, locale=locale))


def _translate_moz_locate_into_google_play_one(locale):
    global _mappings
    if _mappings is None:
        _mappings = utils.load_json_url(_MAPPING_URL)

    return _mappings[locale] if locale in _mappings else locale
