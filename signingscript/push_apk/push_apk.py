#!/usr/bin/env python3

import argparse
import logging


from oauth2client import client

from signingscript.push_apk import googleplay
from signingscript.push_apk.storel10n import StoreL10n

FORMAT = '%(asctime)s - %(filename)s - %(levelname)s - %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__file__)
logger.setLevel(10)


class PushAPK():
    # Google play has currently 3 tracks. Rollout deploys
    # to a limited percentage of users
    TRACK_VALUES = ('production', 'beta', 'alpha', 'rollout')

    PACKAGE_NAME_VALUES = {
        'org.mozilla.fennec_aurora': 'aurora',
        'org.mozilla.firefox_beta': 'beta',
        'org.mozilla.firefox': 'release'
    }

    def __init__(self):
        self.config = self._get_config_from_argv()
        self.translationMgmt = StoreL10n()

    @staticmethod
    def _get_config_from_argv():
        parser = argparse.ArgumentParser(
            description="""Upload the apk of a Firefox app on Google play.

Example for a beta upload:
$ python push_apk.py --package-name org.mozilla.firefox_beta --track production \
--service-account foo@developer.gserviceaccount.com --credentials key.p12 \
--apk-x86=/path/to/fennec-XX.0bY.multi.android-i386.apk \
--apk-armv7-v15=/path/to/fennec-XX.0bY.multi.android-arm-v15.apk""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        parser.add_argument('--package-name', choices=PushAPK.PACKAGE_NAME_VALUES.keys(),
                            help='The Google play name of the app', required=True)
        parser.add_argument('--track', choices=PushAPK.TRACK_VALUES,
                            default='alpha',    # We are not using alpha but we default to it to avoid mistake
                            help='Track on which to upload')

        parser.add_argument('--service-account', help='The service account email', required=True)
        parser.add_argument('--credentials', dest='google_play_credentials_file', type=argparse.FileType(mode='rb'),
                            default='key.p12', help='The p12 authentication file')

        parser.add_argument('--apk-x86', dest='apk_file_x86', type=argparse.FileType(),
                            help='The path to the x86 APK file', required=True)
        parser.add_argument('--apk-armv7-v15', dest='apk_file_armv7_v15', type=argparse.FileType(),
                            help='The path to the ARM v7 API v15 APK file', required=True)

        return parser.parse_args()

    def upload_apks(self, service, apk_files):
        """ Upload the APK to google play

        service -- The session to Google play
        apk_files -- The files
        """
        edit_request = service.edits().insert(body={},
                                              packageName=self.config.package_name)
        package_code = self.PACKAGE_NAME_VALUES[self.config.package_name]
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
                    logger.warning('Aurora is not supported by store_l10n. Skipping what\'s new.')
                else:
                    self._push_whats_new(package_code, service, edit_id, apk_response)

            except client.AccessTokenRefreshError:
                logger.critical('The credentials have been revoked or expired,'
                         'please re-run the application to re-authorize')

        # Set the track for all apk
        service.edits().tracks().update(
            editId=edit_id,
            track=self.config.track,
            packageName=self.config.package_name,
            body={u'versionCodes': versions}).execute()
        logger.info('Application "%s" set to track "%s" for versions %s' %
                 (self.config.package_name, self.config.track, versions))

        # Commit our changes
        commit_request = service.edits().commit(
            editId=edit_id, packageName=self.config.package_name).execute()
        logger.debug('Edit "%s" has been committed' % (commit_request['id']))

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

    def run(self):
        """ Upload the APK files """
        service = googleplay.connect(self.config.service_account, self.config.google_play_credentials_file.name)
        apks = (self.config.apk_file_armv7_v15, self.config.apk_file_x86)
        self.upload_apks(service, apks)


def main(name=None):
    if name == '__main__':
        push_apk = PushAPK()
        push_apk.run()

main(name=__name__)
