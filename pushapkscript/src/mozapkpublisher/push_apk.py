#!/usr/bin/env python

import sys
import argparse
import logging

from mozapkpublisher import googleplay, store_l10n
from mozapkpublisher import apk as apk_helper
from mozapkpublisher.base import Base, ArgumentParser
from mozapkpublisher.exceptions import WrongArgumentGiven, ArmVersionCodeTooHigh
from mozapkpublisher.update_apk_description import create_or_update_listings

logger = logging.getLogger(__name__)


class PushAPK(Base):
    def __init__(self, config=None):
        self.config = self._parse_config(config)
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

    def upload_apks(self, apks):
        [apk_helper.check_if_apk_is_multilocale(apk['file']) for apk in apks.values()]

        edit_service = googleplay.EditService(
            self.config.service_account, self.config.google_play_credentials_file.name, self.config.package_name,
            self.config.dry_run
        )
        create_or_update_listings(edit_service, self.config.package_name)

        for apk in apks.values():
            apk_response = edit_service.upload_apk(apk['file'])
            apk['version_code'] = apk_response['versionCode']
            _create_or_update_whats_new(edit_service, self.config.package_name, apk['version_code'])

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
        self.upload_apks(apks)


def _create_or_update_whats_new(edit_service, package_name, apk_version_code):
    release_channel = googleplay.PACKAGE_NAME_VALUES[package_name]
    locales = store_l10n.get_translations_per_google_play_locale_code(release_channel)

    for google_play_locale_code, translation in locales.items():
        edit_service.update_whats_new(
            google_play_locale_code, apk_version_code, whats_new=translation.get('whatsnew')
        )


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

    from mozapkpublisher import main_logging
    main_logging.init()

    try:
        PushAPK().run()
    except WrongArgumentGiven as e:
        PushAPK.parser.print_help(sys.stderr)
        sys.stderr.write('{}: error: {}\n'.format(PushAPK.parser.prog, e))
        sys.exit(2)


main(__name__)
