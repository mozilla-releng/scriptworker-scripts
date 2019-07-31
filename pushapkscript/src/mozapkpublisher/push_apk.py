#!/usr/bin/env python3

import argparse
from collections import namedtuple
import logging

from mozapkpublisher.common import store, main_logging
from mozapkpublisher.common.apk import add_apk_checks_arguments, extract_and_check_apks_metadata
from mozapkpublisher.common.exceptions import WrongArgumentGiven
from mozapkpublisher.common.store import AmazonStoreEdit

logger = logging.getLogger(__name__)


ExtractedApk = namedtuple('ProcessedApk', ['file', 'metadata'])


def consumer_callback(publish_config):
    apks = ['file', 'file2']
    expected_package_names = ['org.mozilla.fenix']

    def upload_google(package_name, extracted_apks):
        with store.edit('service_account', 'credentials_file', package_name,
                        contact_google_play=True, commit=True) as edit:
            edit.update_app(extracted_apks, publish_config.track, publish_config.rollout_percentage)

    def upload_amazon(package_name, extracted_apks):
        with AmazonStoreEdit.transaction('client_id', 'client_secret', package_name,
                                         contact_server=True, commit=True) as edit:
            edit.update_app(extracted_apks)

    push_apk_callback(apks, upload_amazon if publish_config.target == 'amazon' else upload_google, expected_package_names)


def push_apk_callback(
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
    for package_name, extracted_apks in apks_by_package_name.values():
        upload_apk(package_name, extracted_apks)


def push_apk(
    apks,
    service_account,
    google_play_credentials_file,
    track,
    expected_package_names,
    rollout_percentage=None,
    commit=True,
    contact_google_play=True,
    skip_check_ordered_version_codes=False,
    skip_check_multiple_locales=False,
    skip_check_same_locales=False,
    skip_checks_fennec=False,
):
    """

    Args:
        apks: list of APK files
        service_account: Google Play service account
        google_play_credentials_file: Credentials file to authenticate to Google Play
        track (str): Google Play track to deploy to (e.g.: "nightly"). If "rollout" is chosen, the parameter
            `rollout_percentage` must be specified as well
        expected_package_names (list of str): defines what the expected package name must be.
        rollout_percentage (int): percentage of users to roll out this update to. Must be a number between [0-100].
            This option is only valid if `track` is set to "rollout"
        commit (bool): `False` to do a dry-run
        contact_google_play (bool): `False` to avoid communicating with Google Play. Useful if you're using mock
            credentials.
        skip_checks_fennec (bool): skip Fennec-specific checks
        skip_check_same_locales (bool): skip check to ensure all APKs have the same locales
        skip_check_multiple_locales (bool): skip check to ensure all APKs have more than one locale
        skip_check_ordered_version_codes (bool): skip check to ensure that ensures all APKs have different version codes
            and that the x86 version code > the arm version code

    """
    # We want to tune down some logs, even when push_apk() isn't called from the command line
    main_logging.init()

    apks_metadata_per_paths = extract_and_check_apks_metadata(
        apks,
        expected_package_names,
        skip_checks_fennec,
        skip_check_multiple_locales,
        skip_check_same_locales,
        skip_check_ordered_version_codes,
    )

    # Each distinct product must be uploaded in different Google Play transaction, so we split them
    # by package name here.
    apks_by_package_name = _apks_by_package_name(apks_metadata_per_paths)
    for package_name, extracted_apks in apks_by_package_name.values():
        with store.edit(service_account, google_play_credentials_file.name, package_name,
                        contact_google_play=contact_google_play, commit=commit) as edit:
            all_version_codes = _get_ordered_version_codes(apks_metadata_per_paths)
            edit.update_app(extracted_apks, track, all_version_codes, rollout_percentage)


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

    store.add_general_google_play_arguments(parser)
    add_apk_checks_arguments(parser)

    parser.add_argument(
        '--track',
        action='store',
        required=True,
        help='Track on which to upload'
    )
    parser.add_argument(
        '--rollout-percentage',
        type=int,
        choices=range(0, 101),
        metavar='[0-100]',
        default=None,
        help='The percentage of user who will get the update. Specify only if track is rollout'
    )

    config = parser.parse_args()

    try:
        push_apk(
            config.apks,
            config.service_account,
            config.google_play_credentials_file,
            config.track,
            config.expected_package_names,
            config.rollout_percentage,
            config.commit,
            config.contact_google_play,
            config.skip_check_ordered_version_codes,
            config.skip_check_multiple_locales,
            config.skip_check_same_locales,
            config.skip_checks_fennec
        )
    except WrongArgumentGiven as e:
        parser.error(e)


__name__ == '__main__' and main()
