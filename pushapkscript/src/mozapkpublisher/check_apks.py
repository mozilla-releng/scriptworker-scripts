#!/usr/bin/env python3

import argparse

from mozapkpublisher.common import main_logging
from mozapkpublisher.common.apk import add_apk_checks_arguments, extract_and_check_apks_metadata


def main():
    parser = argparse.ArgumentParser(
        description='Check set of APKs is valid. These checks are also performed in push_apk.py'
    )

    add_apk_checks_arguments(parser)

    config = parser.parse_args()

    main_logging.init()

    extract_and_check_apks_metadata(
        config.apks,
        config.expected_package_names,
        config.skip_checks_fennec,
        config.skip_check_multiple_locales,
        config.skip_check_same_locales,
        config.skip_check_ordered_version_codes,
    )


__name__ == '__main__' and main()
