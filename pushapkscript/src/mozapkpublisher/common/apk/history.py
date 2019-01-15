import logging

from mozapkpublisher.common.googleplay import is_package_name_nightly

logger = logging.getLogger(__name__)


# TODO Bug 1505538: Activate x86-64 once ready
_MAJOR_FIREFOX_VERSIONS_PER_ARCHITECTURE_AND_API_LEVEL = {
    'arm64-v8a': {
        21: {
            'first_firefox_version': 66,    # Bug 1368484
        },
    },
    'armeabi-v7a': {    # Bug 618789
        9: {
            'first_firefox_version': 32,
            'last_firefox_version': 47,     # Bug 1220184
        },
        11: {
            'first_firefox_version': 37,
            'last_firefox_version': 45,     # Bug 1155801
        },
        15: {
            'first_firefox_version': 46,    # Bug 1220184
            'last_firefox_version': 55,     # Bug 1316462
        },
        16: {
            'first_firefox_version': 56,    # Bug 1316462
        },
    },
    'x86': {    # Bug 757909
        9: {
            'first_firefox_version': 32,
            'last_firefox_version': 36,     # Bug 1220184 - No overlap with API-11 (unlike ARM)
        },
        11: {
            'first_firefox_version': 37,
            'last_firefox_version': 45,     # Bug 1155801
        },
        15: {
            'first_firefox_version': 46,    # Bug 1220184
            'last_firefox_version': 55,     # Bug 1316462
        },
        16: {
            'first_firefox_version': 56,    # Bug 1316462
        },
    },
}


def get_expected_combos(firefox_version, package_name):
    combos = set()
    for architecture in _MAJOR_FIREFOX_VERSIONS_PER_ARCHITECTURE_AND_API_LEVEL:
        api_levels = get_expected_api_levels(firefox_version, package_name, architecture)

        for api_level in api_levels:
            combos.add((architecture, api_level))

    if not combos:
        raise ValueError('No combos found for Firefox version {}. Current rules: {2}'.format(
            firefox_version, _MAJOR_FIREFOX_VERSIONS_PER_ARCHITECTURE_AND_API_LEVEL
        ))

    logger.debug(
        'Expected to find these combos for Firefox {}: {}'.format(
            firefox_version, craft_combos_pretty_names(combos)
        )
    )
    return combos


def get_expected_api_levels(firefox_version, package_name, architecture='armeabi-v7a'):
    return [
        api_level
        for api_level, range_dict in _MAJOR_FIREFOX_VERSIONS_PER_ARCHITECTURE_AND_API_LEVEL[architecture].items()
        if (
            _is_firefox_version_in_range(firefox_version, range_dict) and
            # XXX arm64-v8a (aka AArch64) is not planned to ride trains regularly. It may need
            # a couple of cycles to stabilize. That's why we just expect it on Nightly, for now.
            (
                architecture != 'arm64-v8a' or
                architecture == 'arm64-v8a' and is_package_name_nightly(package_name)
            )
        )
    ]


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


def craft_combos_pretty_names(combos):
    return ', '.join([
        '{} API {}+'.format(*combo)
        for combo in combos
    ])
