#!/usr/bin/env python3

import argparse
import logging

from mozapkpublisher.common import googleplay, store_l10n
from mozapkpublisher.common.base import Base

logger = logging.getLogger(__name__)


class UpdateDescriptionAPK(Base):

    @classmethod
    def _init_parser(cls):
        cls.parser = argparse.ArgumentParser(
            description="""Update the descriptions of an application (multilang)

    Example for updating beta:
    $ python update_apk_description.py --service-account foo@developer.gserviceaccount.com \
    --package-name org.mozilla.firefox_beta --credentials key.p12""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        googleplay.add_general_google_play_arguments(cls.parser)
        cls.parser.add_argument('--package-name', choices=store_l10n.STORE_PRODUCT_DETAILS_PER_PACKAGE_NAME.keys(),
                                help='The Google play name of the app', required=True)
        cls.parser.add_argument('--force-locale', help='Force to a specific locale (instead of all)')

    def update_apk_description(self, package_name):
        edit_service = googleplay.EditService(
            self.config.service_account, self.config.google_play_credentials_file.name, self.config.package_name,
            self.config.commit
        )

        moz_locales = [self.config.force_locale] if self.config.force_locale else None
        l10n_strings = store_l10n.get_translations_per_google_play_locale_code(package_name, moz_locales)
        create_or_update_listings(edit_service, self.config.package_name, l10n_strings, moz_locales)
        edit_service.commit_transaction()

    def run(self):
        self.update_apk_description(self.config.package_name)


def create_or_update_listings(edit_service, package_name, l10n_strings, moz_locales=None):
    for google_play_locale_code, translation in l10n_strings.items():
        edit_service.update_listings(
            google_play_locale_code,
            full_description=translation['long_desc'],
            short_description=translation['short_desc'],
            title=translation['title'],
        )
    logger.info('Listing updated for {} locale(s)'.format(len(l10n_strings)))


def main(name=None):
    if name not in ('__main__', None):
        return

    from mozapkpublisher.common import main_logging
    main_logging.init()

    UpdateDescriptionAPK().run()


main(__name__)
