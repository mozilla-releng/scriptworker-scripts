#!/usr/bin/env python

import sys
import argparse
import logging

from oauth2client import client

from mozapkpublisher import googleplay
from mozapkpublisher.apk import check_if_apk_is_multilocale
from mozapkpublisher.base import Base
from mozapkpublisher.exceptions import WrongArgumentGiven
from mozapkpublisher.storel10n import StoreL10n

logger = logging.getLogger(__name__)


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise WrongArgumentGiven(message)


class PushAPK(Base):
    def __init__(self, config=None):
        self.config = self._parse_config(config)
        if self.config.track == 'rollout' and self.config.rollout_percentage is None:
            raise WrongArgumentGiven("When using track='rollout', rollout percentage must be provided too")

        self.translationMgmt = StoreL10n()

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

    def upload_apks(self, service, apk_files):
        """ Upload the APK to google play

        service -- The session to Google play
        apk_files -- The files
        """
        [check_if_apk_is_multilocale(apk_file.name) for apk_file in apk_files]

        edit_request = service.edits().insert(body={},
                                              packageName=self.config.package_name)
        package_code = googleplay.PACKAGE_NAME_VALUES[self.config.package_name]
        result = edit_request.execute()
        edit_id = result['id']
        # Store all the versions to set the tracks (needs to happen
        # at the same time
        versions = []

        # Retrieve the mapping
        self.translationMgmt.load_mapping()

        # For each files, upload it
        for apk_file in apk_files:
            apk_file_name = apk_file.name
            try:
                # Upload the file
                apk_response = service.edits().apks().upload(
                    editId=edit_id,
                    packageName=self.config.package_name,
                    media_body=apk_file_name).execute()
                logger.info('Version code %d has been uploaded. '
                            'Filename "%s" edit_id %s' %
                            (apk_response['versionCode'], apk_file_name, edit_id))

                versions.append(apk_response['versionCode'])

                if 'aurora' in self.config.package_name:
                    logger.warning('Aurora is not supported by the L10n Store (see \
https://github.com/mozilla-l10n/stores_l10n/issues/71). Skipping what\'s new.')
                else:
                    self._push_whats_new(package_code, service, edit_id, apk_response)

            except client.AccessTokenRefreshError:
                logger.critical('The credentials have been revoked or expired,'
                                'please re-run the application to re-authorize')

        upload_body = {u'versionCodes': versions}
        if self.config.rollout_percentage is not None:
            upload_body[u'userFraction'] = self.config.rollout_percentage / 100

        # Set the track for all apk
        service.edits().tracks().update(
            editId=edit_id,
            track=self.config.track,
            packageName=self.config.package_name,
            body=upload_body).execute()
        logger.info('Application "%s" set to track "%s" for versions %s' %
                    (self.config.package_name, self.config.track, versions))

        self._commit_if_needed(service, edit_id)

    def _push_whats_new(self, package_code, service, edit_id, apk_response):
        locales = self.translationMgmt.get_list_locales(package_code)
        locales.append(u'en-US')

        for locale in locales:
            translation = self.translationMgmt.get_translation(package_code, locale)
            whatsnew = translation.get("whatsnew")
            if locale == "en-GB":
                logger.info("Ignoring en-GB as locale")
                continue
            locale = self.translationMgmt.locale_mapping(locale)
            logger.info('Locale "%s" what\'s new has been updated to "%s"'
                        % (locale, whatsnew))

            listing_response = service.edits().apklistings().update(
                editId=edit_id, packageName=self.config.package_name, language=locale,
                apkVersionCode=apk_response['versionCode'],
                body={'recentChanges': whatsnew}).execute()

            logger.info('Listing for language %s was updated.' % listing_response['language'])

    def _commit_if_needed(self, service, edit_id):
        if self.config.dry_run:
            logger.warn('Dry run option was given, transaction not committed.')
        else:
            service.edits().commit(
                editId=edit_id, packageName=self.config.package_name
            ).execute()
            logger.info('Changes committed')

    def run(self):
        """ Upload the APK files """
        service = googleplay.connect(self.config.service_account, self.config.google_play_credentials_file.name)
        apks = (self.config.apk_file_armv7_v15, self.config.apk_file_x86)
        self.upload_apks(service, apks)


if __name__ == '__main__':
    from mozapkpublisher import main_logging
    main_logging.init()

    try:
        push_apk = PushAPK()
        push_apk.run()
    except WrongArgumentGiven as e:
        PushAPK.parser.print_help(sys.stderr)
        sys.stderr.write('{}: error: {}\n'.format(PushAPK.parser.prog, e))
        sys.exit(2)
