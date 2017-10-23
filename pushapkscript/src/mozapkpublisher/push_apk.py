#!/usr/bin/env python

import argparse
import json
import logging
import sys

from mozapkpublisher.common import googleplay, store_l10n
from mozapkpublisher.common import apk as apk_helper
from mozapkpublisher.common.base import Base, ArgumentParser
from mozapkpublisher.common.exceptions import WrongArgumentGiven, ArmVersionCodeTooHigh
from mozapkpublisher.update_apk_description import create_or_update_listings

logger = logging.getLogger(__name__)


class PushAPK(Base):
    def __init__(self, config=None):
        Base.__init__(self, config=config)

        if self.config.track == 'rollout' and self.config.rollout_percentage is None:
            raise WrongArgumentGiven("When using track='rollout', rollout percentage must be provided too")
        if self.config.rollout_percentage is not None and self.config.track != 'rollout':
            raise WrongArgumentGiven("When using rollout-percentage, track must be set to rollout")

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

        google_play_strings_group = cls.parser.add_mutually_exclusive_group(required=True)
        google_play_strings_group.add_argument('--no-gp-string-update', dest='update_google_play_strings', action='store_false',
                                               help="Don't update listings and what's new sections on Google Play")
        google_play_strings_group.add_argument('--update-gp-strings-from-l10n-store', dest='update_google_play_strings_from_store',
                                               action='store_true',
                                               help="Download listings and what's new sections from the l10n store and use them \
                                               to update Google Play")
        google_play_strings_group.add_argument('--update-gp-strings-from-file', dest='google_play_strings_file', type=argparse.FileType(),
                                               help="Use file to update listing and what's new section on Google Play.\
                                               Such file can be obtained by calling fetch_l10n_strings.py")

    def upload_apks(self, apks, l10n_strings=None):
        for architecture, apk in apks.items():
            apk_helper.check_if_apk_has_claimed_architecture(apk['file'], architecture)
            apk_helper.check_if_apk_is_multilocale(apk['file'])

        edit_service = googleplay.EditService(
            self.config.service_account, self.config.google_play_credentials_file.name, self.config.package_name,
            self.config.dry_run
        )

        if l10n_strings is not None:
            create_or_update_listings(edit_service, self.config.package_name, l10n_strings)

        for apk in apks.values():
            apk_response = edit_service.upload_apk(apk['file'])
            apk['version_code'] = apk_response['versionCode']

            if l10n_strings is not None:
                _create_or_update_whats_new(edit_service, self.config.package_name, apk['version_code'], l10n_strings)

        all_version_codes = _check_and_get_flatten_version_codes(apks)
        edit_service.update_track(self.config.track, all_version_codes, self.config.rollout_percentage)
        edit_service.commit_transaction()

    def run(self):
        # Matching version codes will be added during runtime.
        apks = {
            'armv7_v15': {
                'file': self.config.apk_file_armv7_v15.name,
            },
            'x86': {
                'file': self.config.apk_file_x86.name,
            },
        }

        if self.config.google_play_strings_file:
            l10n_strings = json.load(self.config.google_play_strings_file)
            logger.info('Loaded listings and what\'s new section from "{}"'.format(self.config.google_play_strings_file.name))
        elif self.config.update_google_play_strings_from_store:
            logger.info("Downloading listings and what's new section from L10n Store...")
            l10n_strings = store_l10n.get_translations_per_google_play_locale_code(self.config.package_name)
        elif not self.config.update_google_play_strings:
            logger.warn("Listing and what's new section won't be updated.")
            l10n_strings = None
        else:
            raise WrongArgumentGiven("Option missing. You must provide what to do in regards to Google Play strings.")

        self.upload_apks(apks, l10n_strings)


def _create_or_update_whats_new(edit_service, package_name, apk_version_code, l10n_strings):
    if googleplay.is_package_name_nightly(package_name):
        # See https://github.com/mozilla-l10n/stores_l10n/issues/142
        logger.warn("Nightly detected, What's new section won't be updated")
        return

    for google_play_locale_code, translation in l10n_strings.items():
        try:
            whats_new = translation['whatsnew']
            edit_service.update_whats_new(
                google_play_locale_code, apk_version_code, whats_new=whats_new
            )
        except KeyError:
            logger.warn("No What's new section defined for locale {}".format(google_play_locale_code))


def _check_and_get_flatten_version_codes(apks):
    _check_apks_version_codes_are_correctly_ordered(apks)
    return sorted([apk['version_code'] for apk in apks.values()])


def _check_apks_version_codes_are_correctly_ordered(apks):
    # See https://bugzilla.mozilla.org/show_bug.cgi?id=1338477 for more context
    x86_version_code = apks['x86']['version_code']
    arm_version_code = apks['armv7_v15']['version_code']
    if x86_version_code <= arm_version_code:
        raise ArmVersionCodeTooHigh(arm_version_code, x86_version_code)


def main(name=None):
    if name not in ('__main__', None):
        return

    from mozapkpublisher.common import main_logging
    main_logging.init()

    try:
        PushAPK().run()
    except WrongArgumentGiven as e:
        PushAPK.parser.print_help(sys.stderr)
        sys.stderr.write('{}: error: {}\n'.format(PushAPK.parser.prog, e))
        sys.exit(2)


main(__name__)
