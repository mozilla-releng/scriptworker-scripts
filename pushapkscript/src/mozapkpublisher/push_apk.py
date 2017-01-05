#!/usr/bin/env python

import sys
import argparse
import logging

from mozapkpublisher import apk, googleplay, store_l10n
from mozapkpublisher.base import Base, ArgumentParser
from mozapkpublisher.exceptions import WrongArgumentGiven

logger = logging.getLogger(__name__)


class PushAPK(Base):
    def __init__(self, config=None):
        self.config = self._parse_config(config)
        if self.config.track == 'rollout' and self.config.rollout_percentage is None:
            raise WrongArgumentGiven("When using track='rollout', rollout percentage must be provided too")

    @classmethod
    def _init_parser(cls):
        cls.parser = ArgumentParser(
            description="""Upload the apk of a Firefox app on Google play.

    Example for a beta upload:
    $ python push_apk.py --package-name org.mozilla.firefox_beta --track production \
    --service-account foo@developer.gserviceaccount.com --credentials key.p12 \
    --apk-x86=/path/to/fennec-XX.0bY.multi.android-i386.apk \
    --apk-armv7-v15=/path/to/fennec-XX.0bY.multi.android-arm-v15.apk""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        googleplay.add_general_google_play_arguments(cls.parser)

        cls.parser.add_argument('--track', choices=googleplay.TRACK_VALUES, default='alpha',
                                help='Track on which to upload')
        cls.parser.add_argument('--rollout-percentage', type=int, choices=range(0, 101), metavar='[0-100]',
                                default=None,
                                help='The percentage of user who will get the update. Specify only if track is rollout')

        cls.parser.add_argument('--apk-x86', dest='apk_file_x86', type=argparse.FileType(),
                                help='The path to the x86 APK file', required=True)
        cls.parser.add_argument('--apk-armv7-v15', dest='apk_file_armv7_v15', type=argparse.FileType(),
                                help='The path to the ARM v7 API v15 APK file', required=True)

    def upload_apks(self, apk_files):
        """ Upload the APK to google play

        service -- The session to Google play
        apk_files -- The files
        """
        [apk.check_if_apk_is_multilocale(apk_file.name) for apk_file in apk_files]

        edit_service = googleplay.EditService(
            self.config.service_account, self.config.google_play_credentials_file.name, self.config.package_name,
            self.config.dry_run
        )
        release_channel = googleplay.PACKAGE_NAME_VALUES[self.config.package_name]
        # Store all the versions to set the tracks (needs to happen
        # at the same time
        versions = []

        for apk_file in apk_files:
            apk_file_name = apk_file.name
            apk_response = edit_service.upload_apk(apk_file_name)
            versions.append(apk_response['versionCode'])

            if 'aurora' in self.config.package_name:
                logger.warning('Aurora is not supported by the L10n Store (see \
https://github.com/mozilla-l10n/stores_l10n/issues/71). Skipping what\'s new.')
            else:
                _push_whats_new(edit_service, release_channel, apk_response['versionCode'])

        upload_body = {u'versionCodes': versions}
        if self.config.rollout_percentage is not None:
            upload_body[u'userFraction'] = self.config.rollout_percentage / 100.0

        edit_service.update_track(self.config.track, upload_body)
        edit_service.commit_transaction()

    def run(self):
        """ Upload the APK files """
        apks = (self.config.apk_file_armv7_v15, self.config.apk_file_x86)
        self.upload_apks(apks)


def _push_whats_new(edit_service, release_channel, apk_version_code):
    locales = store_l10n.get_list_locales(release_channel)
    locales.append(u'en-US')

    for locale in locales:
        if locale == "en-GB":
            logger.info("Ignoring en-GB as locale")
            continue

        translation = store_l10n.get_translation(release_channel, locale)
        whatsnew = translation.get('whatsnew')
        play_store_locale = store_l10n.locale_mapping(locale)

        edit_service.update_apk_listings(play_store_locale, apk_version_code, body={'recentChanges': whatsnew})
        logger.info(u'Locale "{}" what\'s new has been updated to "{}"'.format(play_store_locale, whatsnew))


def main(name=None):
    if name not in ('__main__', None):
        return

    from mozapkpublisher import main_logging
    main_logging.init()

    try:
        PushAPK().run()
    except WrongArgumentGiven as e:
        PushAPK.parser.print_help(sys.stderr)
        sys.stderr.write('{}: error: {}\n'.format(PushAPK.parser.prog, e))
        sys.exit(2)


main(__name__)
