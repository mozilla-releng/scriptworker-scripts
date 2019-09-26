import argparse

from mozapkpublisher.common.apk.checker import (
    cross_check_apks,
)
from mozapkpublisher.common.apk.extractor import extract_metadata


def add_apk_checks_arguments(parser):
    parser.add_argument('apks', metavar='path_to_apk', type=argparse.FileType(mode='rb'), nargs='+',
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
    parser.add_argument('--expected-package-name', dest='expected_package_names',
                        action='append',
                        help='Package names apks are expected to match',
                        required=True)


def extract_and_check_apks_metadata(
    apks,
    expected_package_names,
    skip_checks_fennec,
    skip_check_multiple_locales,
    skip_check_same_locales,
    skip_check_ordered_version_codes,
):
    apks_metadata = {
        apk: extract_metadata(apk.name, not skip_check_ordered_version_codes,
                              not skip_check_same_locales and not skip_check_multiple_locales,
                              not skip_checks_fennec)
        for apk in apks
    }
    cross_check_apks(
        apks_metadata,
        expected_package_names,
        skip_checks_fennec,
        skip_check_multiple_locales,
        skip_check_same_locales,
        skip_check_ordered_version_codes,
    )

    return apks_metadata
