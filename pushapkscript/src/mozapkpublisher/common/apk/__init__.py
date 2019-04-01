import argparse

from mozapkpublisher.common.apk.checker import (
    AnyPackageNamesCheck,
    ExpectedPackageNamesCheck,
    cross_check_apks,
)
from mozapkpublisher.common.apk.extractor import extract_metadata


def add_apk_checks_arguments(parser):
    parser.add_argument('apks', metavar='path_to_apk', type=argparse.FileType(), nargs='+',
                        help='The path to the APK to upload. You have to provide every APKs for each architecture/API level. \
                                            Missing or extra APKs exit the program without uploading anything')

    parser.add_argument('--skip-check-ordered-version-codes', action='store_true',
                        help='Skip check that asserts version codes are different, x86 code > arm code')
    parser.add_argument('--skip-check-multiple-locales', action='store_true',
                        help='Skip check that asserts that apks all have multiple locales')
    parser.add_argument('--skip-check-same-locales', action='store_true',
                        help='Skip check that asserts that all apks have the same locales')
    parser.add_argument('--skip-checks-fennec', action='store_true',
                        help='Skip checks that are Fennec-specific (ini-checking, checking '
                             'version-to-package-name compliance)')

    expected_package_names_group = parser.add_mutually_exclusive_group(required=True)
    expected_package_names_group.add_argument('--expected-package-name', dest='expected_package_names',
                                              action='append',
                                              help='Package names apks are expected to match')
    expected_package_names_group.add_argument('--skip-check-package-names', action='store_true',
                                              help='Skip assertion that apks match a specified package name')


def extract_and_check_apks_metadata(
    apks,
    expected_package_names,
    skip_check_package_names,
    skip_checks_fennec,
    skip_check_multiple_locales,
    skip_check_same_locales,
    skip_check_ordered_version_codes,
):
    if expected_package_names and not skip_check_package_names:
        package_names_check = ExpectedPackageNamesCheck(expected_package_names)
    elif not expected_package_names and skip_check_package_names:
        package_names_check = AnyPackageNamesCheck()
    else:
        raise ValueError(
            'Either expected_package_names or skip_check_package_names must be truthy. '
            'Values: {}'.format((expected_package_names, skip_check_package_names))
        )

    apks_paths = [apk.name for apk in apks]
    apks_metadata_per_paths = {
        apk_path: extract_metadata(apk_path, not skip_checks_fennec)
        for apk_path in apks_paths
    }
    cross_check_apks(
        apks_metadata_per_paths,
        package_names_check,
        skip_checks_fennec,
        skip_check_multiple_locales,
        skip_check_same_locales,
        skip_check_ordered_version_codes,
    )

    return apks_metadata_per_paths
