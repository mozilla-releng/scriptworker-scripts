import logging

from functools import partial

from mozilla_version.gecko import FennecVersion

from mozapkpublisher.common.apk.history import get_expected_combos, craft_combos_pretty_names
from mozapkpublisher.common.exceptions import BadApk, BadSetOfApks, NotMultiLocaleApk
from mozapkpublisher.common.utils import filter_out_identical_values

logger = logging.getLogger(__name__)


# x86* must have the highest version code. See bug 1338477 for more context.
_ARCHITECTURE_ORDER_REGARDING_VERSION_CODE = ('armeabi-v7a', 'arm64-v8a', 'x86', 'x86_64')


def cross_check_apks(apks_metadata, expected_package_names, skip_checks_fennec, skip_check_multiple_locales,
                     skip_check_same_locales, skip_check_ordered_version_codes):
    logger.info("Checking APKs' metadata and content...")
    _check_package_names(expected_package_names, apks_metadata)

    if not skip_checks_fennec:
        singular_apk_metadata = list(apks_metadata.values())[0]
        _check_version_matches_package_name(
            singular_apk_metadata['firefox_version'], singular_apk_metadata['package_name']
        )

        _check_all_apks_have_the_same_firefox_version(apks_metadata)
        _check_all_apks_have_the_same_build_id(apks_metadata)
        _check_all_architectures_and_api_levels_are_present(apks_metadata)

    if not skip_check_multiple_locales:
        _check_all_apks_are_multi_locales(apks_metadata)

    if not skip_check_same_locales:
        _check_all_apks_have_the_same_locales(apks_metadata)

    if not skip_check_ordered_version_codes:
        _check_apks_version_codes_are_correctly_ordered(apks_metadata)

    logger.info('APKs are sane!')


def _check_package_names(expected_package_names, apks_metadata):
    types = set([metadata['package_name'] for metadata in apks_metadata.values()])

    if not types == set(expected_package_names):
        raise BadSetOfApks(
            'Expected package names {}, found {}'.format(expected_package_names, types))
    logger.info('Found valid package names {}'.format(types))


def _check_piece_of_metadata_is_unique(key, pretty_key, apks_metadata):
    all_items = [metadata[key] for metadata in apks_metadata.values()]
    unique_items = filter_out_identical_values(all_items)

    if not unique_items:
        raise BadSetOfApks('No {} found'.format(key))
    if len(unique_items) > 1:
        raise BadSetOfApks("APKs don't have the same {}. Found: {}".format(pretty_key, unique_items))

    logger.info('All APKs have the same {}: {}'.format(pretty_key, unique_items[0]))


_check_all_apks_have_the_same_firefox_version = partial(_check_piece_of_metadata_is_unique, 'firefox_version', 'Firefox version')
_check_all_apks_have_the_same_build_id = partial(_check_piece_of_metadata_is_unique, 'firefox_build_id', 'Firefox BuildID')
_check_all_apks_have_the_same_locales = partial(_check_piece_of_metadata_is_unique, 'locales', 'locales')


def _check_version_matches_package_name(version, package_name):
    sanitized_version = FennecVersion.parse(version)

    if (
        (package_name == 'org.mozilla.firefox' and sanitized_version.is_release) or
        # Due to project Dawn, Nightly is now using the Aurora package name. See bug 1357351.
        (package_name == 'org.mozilla.fennec_aurora' and sanitized_version.is_nightly) or
        (
            # XXX Betas aren't following the regular XX.YbN format. Instead they follow XX.Y
            # Therefore, we can't use sanitized_version.is_beta
            package_name == 'org.mozilla.firefox_beta'
            and sanitized_version.is_release
            # We ensure the patch_number is undefined. Calling sanitized_version.patch_number
            # directly raises an (expected) AttributeError
            and getattr(sanitized_version, 'patch_number', None) is None
        )
    ):
        logger.info('Firefox version "{}" matches package name "{}"'.format(version, package_name))

    else:
        raise BadApk('Wrong version number "{}" for package name "{}"'.format(version, package_name))


def _check_apks_version_codes_are_correctly_ordered(apks_metadata):
    architectures_per_version_code = {
        metadata['version_code']: metadata['architecture']
        for metadata in apks_metadata.values()
    }

    if len(architectures_per_version_code) != len(apks_metadata):
        raise BadSetOfApks('Some APKs are sharing the same version code! APKs metadata: {}'.format(
            apks_metadata
        ))

    sorted_architectures_per_version_code = tuple([
        architectures_per_version_code[version_code]
        for version_code in sorted(architectures_per_version_code.keys())
    ])

    previous_index = -1
    for architecture in sorted_architectures_per_version_code:
        index = _ARCHITECTURE_ORDER_REGARDING_VERSION_CODE.index(architecture)
        if index <= previous_index:
            raise BadSetOfApks(
                'APKs version codes are not correctly ordered. Expected order: {}. Order found: {}. APKs metadata: {}'.format(
                    _ARCHITECTURE_ORDER_REGARDING_VERSION_CODE, sorted_architectures_per_version_code, apks_metadata
                )
            )
        previous_index = index

    logger.info('APKs version codes are correctly ordered: {}'.format(architectures_per_version_code))


def _check_all_apks_are_multi_locales(apks_metadata):
    for apk, metadata in apks_metadata.items():
        locales = metadata['locales']

        if not isinstance(locales, tuple):
            raise BadApk('Locale list is not either a tuple. "{}" has: {}'.format(apk.name, locales))

        number_of_locales = len(locales)

        if number_of_locales <= 1:
            raise NotMultiLocaleApk(apk.name, locales)

        logger.info('"{}" is multilocale.'.format(apk.name))


def _check_all_architectures_and_api_levels_are_present(apks_metadata):
    single_metadata = list(apks_metadata.values())[0]
    firefox_version = single_metadata['firefox_version']

    expected_combos = get_expected_combos(firefox_version, single_metadata['package_name'])

    current_combos = set([
        (metadata['architecture'], metadata['api_level'])
        for metadata in apks_metadata.values()
    ])

    missing_combos = expected_combos - current_combos
    if missing_combos:
        raise BadSetOfApks('One or several APKs are missing for Firefox {}: {}'.format(
            firefox_version, craft_combos_pretty_names(missing_combos)
        ))

    extra_combos = current_combos - expected_combos
    if extra_combos:
        raise BadSetOfApks('One or several APKs are not allowed for Firefox {}: {}. \
Please make sure mozapkpublisher has allowed them to be uploaded.'.format(
            firefox_version, craft_combos_pretty_names(extra_combos)
        ))

    logger.info('Every expected APK was found!')
