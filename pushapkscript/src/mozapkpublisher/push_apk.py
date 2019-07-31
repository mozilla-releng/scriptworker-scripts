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
        with open(publish_config['google_credentials_file']) as credentials:
            with store.edit(
                publish_config['google_service_account'],
                credentials,
                package_name,
                contact_google_play=True,
                commit=True
            ) as edit:
                edit.update_app(extracted_apks, publish_config['track'],
                                publish_config['rollout_percentage'])

    def upload_amazon(package_name, extracted_apks):
        with AmazonStoreEdit.transaction(
            publish_config['amazon_client_id'],
            publish_config['amazon_client_secret'],
            package_name,
            contact_server=True,
            commit=True
        ) as edit:
            edit.update_app(extracted_apks)

    push_apk_callback(
        apks,
        upload_amazon if publish_config['target_platform'] == 'amazon' else upload_google,
        expected_package_names,
        skip_checks_fennec=True,
    )


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

def consumer(publish_config):
    apks = ['file', 'file2']
    expected_package_names = ['org.mozilla.fenix']

    google_credentials_file = None
    if publish_config['target_platform'] == 'google':
        google_credentials_file = open(publish_config['google_credentials_file'])

    push_apk(
        apks,
        expected_package_names,
        publish_config['target_platform'],
        publish_config.get('amazon_client_id'),
        publish_config.get('amazon_client_secret'),
        publish_config.get('google_service_account'),
        google_credentials_file,
        publish_config.get('google_track'),
        publish_config.get('google_rollout_percentage'),
        commit=True,
        contact_server=True,
        skip_checks_fennec=True,
    )

    if publish_config['target_platform'] == 'google':
        google_credentials_file.close()


def push_apk(
    apks,
    expected_package_names,
    target_platform,
    amazon_client_id=None,
    amazon_client_secret=None,
    google_service_account=None,
    google_credentials_file=None,
    google_track=None,
    google_rollout_percentage=None,
    commit=True,
    contact_server=True,
    skip_check_ordered_version_codes=False,
    skip_check_multiple_locales=False,
    skip_check_same_locales=False,
    skip_checks_fennec=False,
):
    if target_platform == "google" and (
        google_service_account is None
        or google_credentials_file is None
        or google_track is None
    ):
        raise ValueError('When "target_platform" is "google", the account, credentials and track '
                         'must be provided')

    if target_platform == "amazon" and (
        amazon_client_id is None
        or amazon_client_secret is None
    ):
        raise ValueError('When "target_platform" is "amazon", the client_id and client_secret '
                         'must be provided')

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

    # Each distinct product must be uploaded in different "edit"/transaction, so we split them
    # by package name here.
    apks_by_package_name = _apks_by_package_name(apks_metadata_per_paths)
    for package_name, extracted_apks in apks_by_package_name.values():
        if target_platform == 'amazon':
            with AmazonStoreEdit.transaction(amazon_client_id, amazon_client_secret, package_name,
                                             contact_server=contact_server, commit=commit) as edit:
                edit.update_app(extracted_apks)
        elif target_platform == 'google':
            with store.edit(google_service_account, google_credentials_file.name,
                            package_name, contact_google_play=contact_server,
                            commit=commit) as edit:
                edit.update_app(extracted_apks, google_track, google_rollout_percentage)
        else:
            raise ValueError(f'Unexpected target platform of "{target_platform}", expected either'
                             f'"amazon" or "google"')


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
