from mozapkpublisher import utils

# API documentation: https://l10n.mozilla-community.org/stores_l10n/documentation/
L10N_API_URL = 'https://l10n.mozilla-community.org/stores_l10n/'
ALL_LOCALES_URL = L10N_API_URL + 'api/v1/fx_android/listing/{channel}/'
LOCALE_URL = L10N_API_URL + 'api/v1/fx_android/translation/{channel}/{locale}/'
MAPPING_URL = L10N_API_URL + 'api/v1/google/localesmapping/?reverse'

_mappings = None


def get_list_locales(release_channel):
    """ Get all the translated locales supported by Google play
    So, locale unsupported by Google play won't be downloaded
    Idem for not translated locale
    """
    return utils.load_json_url(ALL_LOCALES_URL.format(channel=release_channel))


def get_translation(release_channel, locale):
    """ Get the translation for a locale
    """
    return utils.load_json_url(LOCALE_URL.format(channel=release_channel, locale=locale))


def locale_mapping(locale):
    """ Google play and Mozilla don't have the exact locale code
    Translate them
    """
    global _mappings
    if _mappings is None:
        _mappings = utils.load_json_url(MAPPING_URL)

    return _mappings[locale] if locale in _mappings else locale
