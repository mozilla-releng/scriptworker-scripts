#!/usr/bin/env python3

import argparse
import json
import logging

from argparse import ArgumentParser
from mozapkpublisher.common import store_l10n

logger = logging.getLogger(__name__)


def get_l10n_strings(package_name, output_file):
    l10n_strings = store_l10n.get_translations_per_google_play_locale_code(package_name)
    json.dump(l10n_strings, output_file)


def main():
    from mozapkpublisher.common import main_logging
    main_logging.init()

    parser = ArgumentParser(
        description='Download strings from the l10n store ({})'.format(store_l10n.L10N_API_URL)
    )

    parser.add_argument('--package-name', choices=store_l10n.STORE_PRODUCT_DETAILS_PER_PACKAGE_NAME.keys(),
                        help='The APK package name', required=True)
    parser.add_argument('--output-file', type=argparse.FileType('w'),
                        help='The file where strings will be saved to',
                        default='l10n_strings.json')

    config = parser.parse_args()
    get_l10n_strings(config.package_name, config.output_file)


__name__ == '__main__' and main()
