#!/usr/bin/env python3

import argparse
import json
import logging

from mozapkpublisher.common import store_l10n
from mozapkpublisher.common.base import Base, ArgumentParser

logger = logging.getLogger(__name__)


class GetL10nStrings(Base):
    @classmethod
    def _init_parser(cls):
        cls.parser = ArgumentParser(
            description='Download strings from the l10n store ({})'.format(store_l10n.L10N_API_URL)
        )

        cls.parser.add_argument('--package-name', choices=store_l10n.STORE_PRODUCT_DETAILS_PER_PACKAGE_NAME.keys(),
                                help='The APK package name', required=True)
        cls.parser.add_argument('--output-file', type=argparse.FileType('w'), help='The file where strings will be saved to',
                                default='l10n_strings.json')

    def run(self):
        l10n_strings = store_l10n.get_translations_per_google_play_locale_code(self.config.package_name)
        json.dump(l10n_strings, self.config.output_file)


def main(name=None):
    if name not in ('__main__', None):
        return

    from mozapkpublisher.common import main_logging
    main_logging.init()

    GetL10nStrings().run()


main(__name__)
