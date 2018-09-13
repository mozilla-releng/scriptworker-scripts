import logging

from functools import partial

from mozilla_version.gecko import FennecVersion

from mozapkpublisher.common.apk.history import get_expected_api_levels_for_version, get_expected_architectures_for_version
from mozapkpublisher.common.exceptions import BadApk, BadSetOfApks, NotMultiLocaleApk
from mozapkpublisher.common.utils import filter_out_identical_values, PRODUCT

logger = logging.getLogger(__name__)


# x86 must have the highest version code. See bug 1338477 for more context.
# TODO: Support ARM64, once bug 1368484 is ready
_ARCHITECTURE_ORDER_REGARDING_VERSION_CODE = ('armeabi-v7a', 'x86')


def cross_check_apks(apks_metadata_per_paths):
    logger.info("Checking APKs' metadata and content...")
    if PRODUCT.is_focus_flavor(list(apks_metadata_per_paths.values())[0]['package_name']):
        cross_check_focus_apks(apks_metadata_per_paths)
    else:
        cross_check_fennec_apks(apks_metadata_per_paths)


def cross_check_fennec_apks(apks_metadata_per_paths):
    _check_all_apks_have_the_same_package_name(apks_metadata_per_paths)
    _check_all_apks_have_the_same_version(apks_metadata_per_paths)

    singular_apk_metadata = list(apks_metadata_per_paths.values())[0]
    _check_version_matches_package_name(
        singular_apk_metadata['firefox_version'], singular_apk_metadata['package_name']
    )

    _check_all_apks_have_the_same_build_id(apks_metadata_per_paths)
    _check_apks_version_codes_are_correctly_ordered(apks_metadata_per_paths)

    _check_all_apks_are_multi_locales(apks_metadata_per_paths)
    _check_all_apks_have_the_same_locales(apks_metadata_per_paths)

    _check_all_architectures_and_api_levels_are_present(apks_metadata_per_paths)

    logger.info('APKs are sane!')


def cross_check_focus_apks(apks_metadata_per_paths):
    _check_number_of_distinct_packages(apks_metadata_per_paths, 2)
    _check_correct_apk_product_types(apks_metadata_per_paths, [PRODUCT.FOCUS, PRODUCT.KLAR])
    logger.info('APKs are sane!')


def _check_number_of_distinct_packages(apks_metadata_per_paths, max_packages):
    all_items = [metadata['package_name'] for metadata in apks_metadata_per_paths.values()]
    unique_packages = filter_out_identical_values(all_items)
    if (len(unique_packages) > max_packages):
        raise BadSetOfApks('Expected max {} package names, found {}'.format(max_packages, len(unique_packages)))
    logger.info('Found expected number of package names, not more than {}'.format(max_packages))


def _check_correct_apk_product_types(apks_metadata_per_paths, product_types):
    types = set([PRODUCT.get_value_or_none(metadata['package_name']) for metadata in apks_metadata_per_paths.values()])
    if not types.issubset(product_types):
        raise BadSetOfApks('Expected product types {}, found {}'.format(product_types, types))
    logger.info('Expected product types {} found'.format(product_types))


def _check_piece_of_metadata_is_unique(key, pretty_key, apks_metadata_per_paths):
    all_items = [metadata[key] for metadata in apks_metadata_per_paths.values()]
    unique_items = filter_out_identical_values(all_items)

    if not unique_items:
        raise BadSetOfApks('No {} found'.format(key))
    if len(unique_items) > 1:
        raise BadSetOfApks("APKs don't have the same {}. Found: {}".format(pretty_key, unique_items))

    logger.info('All APKs have the same {}: {}'.format(pretty_key, unique_items[0]))


_check_all_apks_have_the_same_package_name = partial(_check_piece_of_metadata_is_unique, 'package_name', 'package name')
_check_all_apks_have_the_same_version = partial(_check_piece_of_metadata_is_unique, 'firefox_version', 'Firefox version')
_check_all_apks_have_the_same_build_id = partial(_check_piece_of_metadata_is_unique, 'firefox_build_id', 'Firefox BuildID')
_check_all_apks_have_the_same_locales = partial(_check_piece_of_metadata_is_unique, 'locales', 'locales')


def _check_version_matches_package_name(version, package_name):
    sanitized_version = FennecVersion.parse(version)

    if (
        (package_name == 'org.mozilla.firefox' and sanitized_version.is_release) or
        # Due to project Dawn, Nightly is now using the Aurora package name. See bug 1357351.
        (package_name == 'org.mozilla.fennec_aurora' and sanitized_version.is_nightly) or
        (
            # XXX Betas aren't following the regular XX.0bY format. Instead they follow XX.0
            # (which looks like release). Therefore, we can't use sanitized_version.is_beta
            package_name == 'org.mozilla.firefox_beta'
            and sanitized_version.is_release
            and sanitized_version.minor_number == 0
            # We ensure the patch_number is undefined. Calling sanitized_version.patch_number
            # directly raises an (expected) AttributeError
            and getattr(sanitized_version, 'patch_number', None) is None
        )
    ):
        logger.info('Firefox version "{}" matches package name "{}"'.format(version, package_name))

    else:
        raise BadApk('Wrong version number "{}" for package name "{}"'.format(version, package_name))


def _check_apks_version_codes_are_correctly_ordered(apks_metadata_per_paths):
    architectures_per_version_code = {
        metadata['version_code']: metadata['architecture']
        for metadata in apks_metadata_per_paths.values()
    }

    if len(architectures_per_version_code) != len(apks_metadata_per_paths):
        raise BadSetOfApks('Some APKs are sharing the same version code! APKs metadata: {}'.format(
            apks_metadata_per_paths
        ))

    sorted_architectures_per_version_code = tuple([
        architectures_per_version_code[version_code]
        for version_code in sorted(architectures_per_version_code.keys())
    ])

    if sorted_architectures_per_version_code != _ARCHITECTURE_ORDER_REGARDING_VERSION_CODE:
        raise BadSetOfApks(
            'APKs version codes are not correctly ordered. Expected order: {}. Order found: {}. APKs metadata: {}'.format(
                _ARCHITECTURE_ORDER_REGARDING_VERSION_CODE, sorted_architectures_per_version_code, apks_metadata_per_paths
            )
        )

    logger.info('APKs version codes are correctly ordered: {}'.format(architectures_per_version_code))


def _check_all_apks_are_multi_locales(apks_metadata_per_paths):
    for path, metadata in apks_metadata_per_paths.items():
        locales = metadata['locales']

        if not isinstance(locales, tuple):
            raise BadApk('Locale list is not either a tuple. "{}" has: {}'.format(path, locales))

        number_of_locales = len(locales)

        if number_of_locales <= 1:
            raise NotMultiLocaleApk(path, locales)

        logger.info('"{}" is multilocale.'.format(path))


def _check_all_architectures_and_api_levels_are_present(apks_metadata_per_paths):
    firefox_version = list(apks_metadata_per_paths.values())[0]['firefox_version']
    expected_api_levels = get_expected_api_levels_for_version(firefox_version)
    expected_architectures = get_expected_architectures_for_version(firefox_version)
    expected_combos = _craft_expected_combos(firefox_version, expected_api_levels, expected_architectures)

    current_combos = set([
        (metadata['architecture'], metadata['api_level'])
        for metadata in apks_metadata_per_paths.values()
    ])

    missing_combos = expected_combos - current_combos
    if missing_combos:
        raise BadSetOfApks('One or several APKs are missing for Firefox {}: {}'.format(
            firefox_version, _craft_combos_pretty_names(missing_combos)
        ))

    extra_combos = current_combos - expected_combos
    if extra_combos:
        raise BadSetOfApks('One or several APKs are not allowed for Firefox {}: {}. \
Please make sure mozapkpublisher has allowed them to be uploaded.'.format(
            firefox_version, _craft_combos_pretty_names(extra_combos)
        ))

    logger.info('Every expected APK was found!')


def _craft_expected_combos(firefox_version, expected_api_levels, expected_architectures):
    highest_api_level = max(expected_api_levels)
    expected_combos = []
    for architecture in expected_architectures:
        if architecture == 'armeabi-v7a':
            # We sometimes ship ARMs with several API levels
            for api_level in expected_api_levels:
                expected_combos.append((architecture, api_level))
        else:
            expected_combos.append((architecture, highest_api_level))

    logger.info('{} APKs are expected for Firefox {}: {}'.format(
        len(expected_combos), firefox_version, _craft_combos_pretty_names(expected_combos)
    ))
    return set(expected_combos)


def _craft_combos_pretty_names(combos):
    return ', '.join([
        '{} API {}+'.format(*combo)
        for combo in combos
    ])
