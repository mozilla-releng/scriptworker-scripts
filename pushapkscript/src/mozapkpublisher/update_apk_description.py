#!/usr/bin/env python

import argparse
import logging

from mozapkpublisher import googleplay, store_l10n
from mozapkpublisher.base import Base
from mozapkpublisher.exceptions import WrongArgumentGiven

logger = logging.getLogger(__name__)


class UpdateDescriptionAPK(Base):

    def __init__(self, config=None):
        self.config = self._parse_config(config)

        if 'aurora' in self.config.package_name:
            raise WrongArgumentGiven('Aurora is not yet supported by the L10n Store. \
See bug https://github.com/mozilla-l10n/stores_l10n/issues/71')

    @classmethod
    def _init_parser(cls):
        cls.parser = argparse.ArgumentParser(
            description="""Update the descriptions of an application (multilang)

    Example for updating beta:
    $ python update_apk_description.py --service-account foo@developer.gserviceaccount.com \
    --package-name org.mozilla.firefox_beta --credentials key.p12 --update-apk-description""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        googleplay.add_general_google_play_arguments(cls.parser)
        cls.parser.add_argument('--force-locale', help='Force to a specific locale (instead of all)')

    def update_apk_description(self, package_name):
        edit_service = googleplay.EditService(
            self.config.service_account, self.config.google_play_credentials_file.name, self.config.package_name,
            self.config.dry_run
        )

        release_channel = googleplay.PACKAGE_NAME_VALUES[self.config.package_name]

        locales = [self.config.force_locale] if self.config.force_locale \
            else store_l10n.get_list_locales(release_channel)

        for locale in locales:
            translation = store_l10n.get_translation(release_channel, locale)
            google_play_locale = store_l10n.locale_mapping(locale)
            edit_service.update_listings(google_play_locale, body={
                'fullDescription': translation.get('long_desc'),
                'shortDescription': translation.get('short_desc'),
                'title': translation.get('title')
            })

        edit_service.commit_transaction()
        logger.info('Done. {} locale(s) updated'.format(len(locales)))

    def run(self):
        self.update_apk_description(self.config.package_name)


def main(name=None):
    if name not in ('__main__', None):
        return

    from mozapkpublisher import main_logging
    main_logging.init()

    UpdateDescriptionAPK().run()


main(__name__)
