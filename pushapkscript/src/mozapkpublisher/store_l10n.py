import logging

from mozapkpublisher import utils

# API documentation: https://l10n.mozilla-community.org/stores_l10n/documentation/
L10N_API_URL = 'https://l10n.mozilla-community.org/stores_l10n/'
ALL_LOCALES_URL = L10N_API_URL + 'api/v1/fx_android/listing/{channel}/'
LOCALE_URL = L10N_API_URL + 'api/v1/fx_android/translation/{channel}/{locale}/'
MAPPING_URL = L10N_API_URL + 'api/v1/google/localesmapping/?reverse'

logger = logging.getLogger(__name__)

_mappings = None
_translations_per_google_play_locale_code = None


def get_translations_per_google_play_locale_code(release_channel, moz_locales=None):
    global _translations_per_google_play_locale_code

    _init_full_locales_if_needed(release_channel)

    return _translations_per_google_play_locale_code if moz_locales is None else {
        _translate_moz_locate_into_google_play_one(moz_locale):
        _translations_per_google_play_locale_code[
            _translate_moz_locate_into_google_play_one(moz_locale)
        ]
        for moz_locale in moz_locales
    }


def _init_full_locales_if_needed(release_channel):
    global _translations_per_google_play_locale_code

    if _translations_per_google_play_locale_code is None:
        moz_locales = _get_list_of_completed_locales(release_channel)
        moz_locales.append(u'en-US')

        logger.info('Downloading {} locales: {}...'.format(
            len(moz_locales), moz_locales
        ))
        _translations_per_google_play_locale_code = {
            _translate_moz_locate_into_google_play_one(moz_locale): _get_translation(release_channel, moz_locale)
            for moz_locale in moz_locales
        }
        logger.info('Locales downloaded and converted to: {}'.format(
            _translations_per_google_play_locale_code.keys()
        ))


def _get_list_of_completed_locales(release_channel):
    """ Get all the translated locales supported by Google play
    So, locale unsupported by Google play won't be downloaded
    Idem for not translated locale
    """
    return utils.load_json_url(ALL_LOCALES_URL.format(channel=release_channel))


def _get_translation(release_channel, locale):
    return utils.load_json_url(LOCALE_URL.format(channel=release_channel, locale=locale))


def _translate_moz_locate_into_google_play_one(locale):
    global _mappings
    if _mappings is None:
        _mappings = utils.load_json_url(MAPPING_URL)

    return _mappings[locale] if locale in _mappings else locale
