import logging

logger = logging.getLogger(__name__)


_MAJOR_FIREFOX_VERSIONS_PER_API_LEVEL = {
    9: {
        'first_firefox_version': 32,
        'last_firefox_version': 47,    # Bug 1220184
    },
    11: {
        'first_firefox_version': 37,
        'last_firefox_version': 45,    # Bug 1155801
    },
    15: {
        'first_firefox_version': 46,   # Bug 1220184
        'last_firefox_version': 55,    # Bug 1316462
    },
    16: {
        'first_firefox_version': 56,   # Bug 1316462
    }
}

# TODO: Support ARM64, once bug 1368484 is ready
_MAJOR_FIREFOX_VERSIONS_PER_ARCHITECTURE = {
    'armeabi-v7a': {
        'first_firefox_version': 4,      # Bug 618789
    },
    'x86': {
        'first_firefox_version': 14,    # Bug 757909
    },
}


def get_expected_api_levels_for_version(firefox_version):
    return _get_expected_things_for_version(firefox_version, _MAJOR_FIREFOX_VERSIONS_PER_API_LEVEL, 'API level')


def get_expected_architectures_for_version(firefox_version):
    return _get_expected_things_for_version(firefox_version, _MAJOR_FIREFOX_VERSIONS_PER_ARCHITECTURE, 'architecture')


def _get_expected_things_for_version(firefox_version, dict_of_things, thing_name):
    things = tuple(sorted([
        thing
        for thing, range_dict in dict_of_things.items()
        if _is_firefox_version_in_range(firefox_version, range_dict)
    ]))

    if not things:
        raise Exception('No {0} found for Firefox version {1}. Current rules for {0}: {2}'.format(
            thing_name, firefox_version, dict_of_things
        ))

    logger.debug('Expected to find these {}s for Firefox {}: {}'.format(thing_name, firefox_version, things))
    return things


def _is_firefox_version_in_range(firefox_version, range_dict):
    first_firefox_version = range_dict['first_firefox_version']
    current_major_version = get_firefox_major_version_number(firefox_version)
    if current_major_version < first_firefox_version:
        return False

    last_firefox_version = range_dict.get('last_firefox_version', None)
    if last_firefox_version is not None and current_major_version > last_firefox_version:
        return False

    return True


def get_firefox_major_version_number(version):
    return int(version.split('.')[0])
