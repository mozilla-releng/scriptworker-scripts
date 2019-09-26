#!/usr/bin/env python3

import argparse
import logging

from mozapkpublisher.common import main_logging
from mozapkpublisher.common.apk import add_apk_checks_arguments, extract_and_check_apks_metadata
from mozapkpublisher.common.exceptions import WrongArgumentGiven
from mozapkpublisher.common.store import AmazonStoreEdit, GooglePlayEdit

logger = logging.getLogger(__name__)


_STORE_PER_TARGET_PLATFORM = {
    'amazon': AmazonStoreEdit,
    'google': GooglePlayEdit,
}


def push_apk(
    apks,
    target_store,
    username,
    secret,
    expected_package_names,
    track=None,
    rollout_percentage=None,
    dry_run=True,
    contact_server=True,
    skip_check_ordered_version_codes=False,
    skip_check_multiple_locales=False,
    skip_check_same_locales=False,
    skip_checks_fennec=False,
):
    """
    Args:
        apks: list of APK files
        target_store (str): either "google" or "amazon", affects what other parameters will need
            to be provided to this function
        username (str): Google Play service account or Amazon Store client ID
        secret (str): Filename of Google Play Credentials file or contents of Amazon Store
            client secret
        expected_package_names (list of str): defines what the expected package names must be.
        track (str): (only when `target_store` is "google") Google Play track to deploy
            to (e.g.: "nightly"). If "rollout" is chosen, the parameter `rollout_percentage` must
            be specified as well
        rollout_percentage (int): percentage of users to roll out this update to. Must be a number
            in (0-100]. This option is only valid if `target_store` is "google" and
            `track` is set to "rollout"
        dry_run (bool): `True` to do a dry-run
        contact_server (bool): `False` to avoid communicating with the Google Play server or Amazon
            Store server. Useful if you're using mock credentials.
        skip_checks_fennec (bool): skip Fennec-specific checks
        skip_check_same_locales (bool): skip check to ensure all APKs have the same locales
        skip_check_multiple_locales (bool): skip check to ensure all APKs have more than one locale
        skip_check_ordered_version_codes (bool): skip check to ensure that ensures all APKs have different version codes
            and that the x86 version code > the arm version code
    """
    if target_store == "google" and track is None:
        # The Google store allows multiple stability "tracks" to exist for a single app, so it
        # requires you to disambiguate which track you'd like to publish to.
        raise WrongArgumentGiven('When "target_store" is "google", the track must be provided')
    if target_store == "amazon":
        # The Amazon app doesn't have a stability "tracks" tool like Google. It _does_ have a
        # "Live App Testing" mechanism, but you have to use the website to use it (the API
        # doesn't support it). So, it's always the "production" app that's updated, and there's
        # no need to specify "track"
        # Source:  "Play Store API supports additional resources (such as testers and tracks) that
        # the [Amazon] Appstore currently does not support."
        # https://developer.amazon.com/docs/app-submission-api/migrate.html
        if track is not None:
            raise WrongArgumentGiven('Tracks are not supported on Amazon')
        if rollout_percentage is not None:
            raise WrongArgumentGiven('Rollout percentage is not supported on Amazon')

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

    update_app_kwargs = {
        kwarg_name: kwarg_value
        for kwarg_name, kwarg_value in (
            ('track', track),
            ('rollout_percentage', rollout_percentage)
        )
        if kwarg_value
    }

    # Each distinct product must be uploaded in different "edit"/transaction, so we split them
    # by package name here.
    apks_by_package_name = _apks_by_package_name(apks_metadata_per_paths)
    for package_name, extracted_apks in apks_by_package_name.items():
        store = _STORE_PER_TARGET_PLATFORM[target_store]
        with store.transaction(username, secret, package_name, contact_server=contact_server,
                               dry_run=dry_run) as edit:
            edit.update_app(extracted_apks, **update_app_kwargs)


def _apks_by_package_name(apks_metadata):
    apk_package_names = {}
    for (apk, metadata) in apks_metadata.items():
        package_name = metadata['package_name']
        if package_name not in apk_package_names:
            apk_package_names[package_name] = []
        apk_package_names[package_name].append((apk, metadata))

    return apk_package_names


def main():
    parser = argparse.ArgumentParser(description='Upload APKs on the Google Play Store.')

    subparsers = parser.add_subparsers(dest='target_store', title='Target Store')

    google_parser = subparsers.add_parser('google')
    google_parser.add_argument('track', help='Track on which to upload')
    google_parser.add_argument(
        '--rollout-percentage',
        type=int,
        choices=range(0, 101),
        metavar='[0-100]',
        default=None,
        help='The percentage of user who will get the update. Specify only if track is rollout'
    )
    google_parser.add_argument('--commit', action='store_false', dest='dry_run',
                               help='Commit new release on Google Play. This action cannot be '
                                    'reverted')

    amazon_parser = subparsers.add_parser('amazon')
    amazon_parser.add_argument('--keep', action='store_false', dest='dry_run',
                               help='Keep "upcoming version" on Amazon to be submitted or '
                                    'cancelled on the Amazon Developer Web UI.')

    parser.add_argument('--username', required=True,
                        help='Either the amazon client id or the google service account')
    parser.add_argument('--secret', required=True,
                        help='Either the amazon client secret or the file that contains '
                             'google credentials')
    parser.add_argument('--do-not-contact-server', action='store_false', dest='contact_server',
                        help='''Prevent any request to reach the APK server. Use this option if
you want to run the script without any valid credentials nor valid APKs. --service-account and
--credentials must still be provided (you can just fill them with random string and file).''')
    add_apk_checks_arguments(parser)
    config = parser.parse_args()

    if config.target_store == 'google':
        track = config.track
        rollout_percentage = config.rollout_percentage
    else:
        track = None
        rollout_percentage = None

    try:
        push_apk(
            config.apks,
            config.target_store,
            config.username,
            config.secret,
            config.expected_package_names,
            track,
            rollout_percentage,
            config.dry_run,
            config.contact_server,
            config.skip_check_ordered_version_codes,
            config.skip_check_multiple_locales,
            config.skip_check_same_locales,
            config.skip_checks_fennec
        )
    except WrongArgumentGiven as e:
        parser.error(e)


__name__ == '__main__' and main()
