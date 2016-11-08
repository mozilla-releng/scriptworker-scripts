#!/usr/bin/env python

import argparse
import logging

from oauth2client import client

from mozapkpublisher import googleplay
from mozapkpublisher.base import Base
from mozapkpublisher.exceptions import WrongArgumentGiven
from mozapkpublisher.storel10n import StoreL10n

logger = logging.getLogger(__name__)


class UpdateDescriptionAPK(Base):

    def __init__(self, config=None):
        self.config = self._parse_config(config)

        if 'aurora' in self.config.package_name:
            raise WrongArgumentGiven('Aurora is not yet supported by the L10n Store. \
See bug https://github.com/mozilla-l10n/stores_l10n/issues/71')

        self.all_locales_url = self.config.l10n_api_url + "api/?done&channel={channel}"
        self.locale_url = self.config.l10n_api_url + "api/?locale={locale}&channel={channel}"
        self.mapping_url = self.config.l10n_api_url + "api/?locale_mapping&reverse"
        self.translationMgmt = StoreL10n()

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

        cls.parser.add_argument('--l10n-api-url', default='https://l10n.mozilla-community.org/stores_l10n/',
                                help='The L10N URL')

        cls.parser.add_argument('--force-locale', help='Force to a specific locale (instead of all)')

    def update_desc(self, service, package_name):
        edit_request = service.edits().insert(body={},
                                              packageName=package_name)
        result = edit_request.execute()
        edit_id = result['id']

        # Retrieve the mapping
        self.translationMgmt.load_mapping()
        package_code = googleplay.PACKAGE_NAME_VALUES[self.config.package_name]

        if self.config.force_locale:
            # The user forced a locale, don't need to retrieve the full list
            locales = [self.config.force_locale]
        else:
            # Get all the locales from the web interface
            locales = self.translationMgmt.get_list_locales(package_code)
        nb_locales = 0
        for locale in locales:
            translation = self.translationMgmt.get_translation(package_code, locale)
            title = translation.get("title")
            short_desc = translation.get("short_desc")
            long_desc = translation.get("long_desc")

            # Google play expects some locales codes (de-DE instead of de)
            locale = self.translationMgmt.locale_mapping(locale)

            try:
                logger.info("Updating " + package_code + " for '" + locale +
                            "' /  title: '" + title + "', short_desc: '" +
                            short_desc[0:20] + "'..., long_desc: '" +
                            long_desc[0:20] + "...'")
                service.edits().listings().update(
                    editId=edit_id, packageName=package_name, language=locale,
                    body={'fullDescription': long_desc,
                          'shortDescription': short_desc,
                          'title': title}).execute()
                nb_locales += 1
            except client.AccessTokenRefreshError:
                logger.info('The credentials have been revoked or expired,'
                            'please re-run the application to re-authorize')

        self._commit_if_needed(service, edit_id, nb_locales)

    def _commit_if_needed(self, service, edit_id, nb_locales):
        if self.config.dry_run:
            logger.warn('Dry run option was given, transaction not committed.')
        else:
            service.edits().commit(
                editId=edit_id, packageName=self.config.package_name
            ).execute()
            logger.info('Changes committed. %d locale(s) updated'.format(nb_locales))

    def update_apk_description(self):
        """ Update the description """
        service = googleplay.connect(self.config.service_account, self.config.google_play_credentials_file.name)
        self.update_desc(service, self.config.package_name)

    def run(self):
        self.update_apk_description()


if __name__ == '__main__':
    from mozapkpublisher import main_logging
    main_logging.init()

    myScript = UpdateDescriptionAPK()
    myScript.run()
