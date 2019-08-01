#!/usr/bin/env python3

import argparse
from collections import namedtuple
import logging

from mozapkpublisher.common import store, main_logging
from mozapkpublisher.common.apk import add_apk_checks_arguments, extract_and_check_apks_metadata
from mozapkpublisher.common.exceptions import WrongArgumentGiven
from mozapkpublisher.common.store import AmazonStoreEdit, GooglePlayEdit

logger = logging.getLogger(__name__)


ExtractedApk = namedtuple('ProcessedApk', ['file', 'metadata'])


def push_apk(
    apks,
    upload_apk,
    expected_package_names,
    skip_check_ordered_version_codes=False,
    skip_check_multiple_locales=False,
    skip_check_same_locales=False,
    skip_checks_fennec=False,
):
    # We want to tune down some logs, even when push_apk() isn't called from the command line
    main_logging.init()

    apks_metadata = extract_and_check_apks_metadata(
        apks,
        expected_package_names,
        skip_checks_fennec,
        skip_check_multiple_locales,
        skip_check_same_locales,
        skip_check_ordered_version_codes,
    )

    # Each distinct product must be uploaded in different store transaction, so we split them
    # by package name here.
    apks_by_package_name = _apks_by_package_name(apks_metadata)
    for package_name, extracted_apks in apks_by_package_name.items():
        upload_apk(package_name, extracted_apks)


def _apks_by_package_name(apks_metadata):
    apk_package_names = {}
    for (apk, metadata) in apks_metadata.items():
        package_name = metadata['package_name']
        if package_name not in apk_package_names:
            apk_package_names[package_name] = []
        apk_package_names[package_name].append(ExtractedApk(apk, metadata))

    return apk_package_names


def _get_ordered_version_codes(apks):
    return sorted([apk['version_code'] for apk in apks.values()])


def main():
    parser = argparse.ArgumentParser(description='Upload APKs on the Google Play Store.')

    subparsers = parser.add_subparsers(dest='target_platform', required=True,
                                       title='Target Platform')

    google_parser = subparsers.add_parser('google')
    google_parser.add_argument('track', help='Track on which to upload')
    google_parser.add_argument('--service-account', help='The service account email', required=True)
    google_parser.add_argument('--credentials', dest='google_play_credentials_file', type=argparse.FileType(mode='rb'), help='The p12 authentication file', required=True)
    google_parser.add_argument(
        '--rollout-percentage',
        type=int,
        choices=range(0, 101),
        metavar='[0-100]',
        default=None,
        help='The percentage of user who will get the update. Specify only if track is rollout'
    )

    amazon_parser = subparsers.add_parser('amazon')
    amazon_parser.add_argument('--client-id', help='The amazon client id for auth', required=True)
    amazon_parser.add_argument('--client-secret', help='The amazon client secret for auth', required=True)

    parser.add_argument('--do_not_contact-server', action='store_false', dest='contact_server',
                        help='''Prevent any request to reach the APK server. Use this option if 
you want to run the script without any valid credentials nor valid APKs. --service-account and 
--credentials must still be provided (you can just fill them with random string and file).''')
    parser.add_argument('--commit', action='store_true', help="Commit changes onto APK server. "
                                                              "This action cannot be reverted.")
    add_apk_checks_arguments(parser)
    config = parser.parse_args()

    def upload_google(package_name, extracted_apks):
        with GooglePlayEdit.transaction(config.service_account,
                                        config.google_play_credentials_file, package_name,
                                        contact_server=config.contact_server, commit=config.commit) as edit:
            edit.update_app(extracted_apks, config.track,
                            config.rollout_percentage)

    def upload_amazon(package_name, extracted_apks):
        with AmazonStoreEdit.transaction(
            config.client_id,
            config.client_secret,
            package_name,
            contact_server=config.contact_server,
            commit=config.commit
        ) as edit:
            edit.update_app(extracted_apks)

    try:
        push_apk(
            config.apks,
            upload_amazon if config.target_platform == 'amazon' else upload_google,
            config.expected_package_names,
            config.skip_check_ordered_version_codes,
            config.skip_check_multiple_locales,
            config.skip_check_same_locales,
            config.skip_checks_fennec
        )
    except WrongArgumentGiven as e:
        parser.error(e)


__name__ == '__main__' and main()
