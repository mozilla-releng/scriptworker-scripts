#!/usr/bin/env python3

import argparse
import logging

from mozapkpublisher.common import main_logging
from mozapkpublisher.common.aab import add_aab_checks_arguments, extract_aabs_metadata
from mozapkpublisher.common.exceptions import WrongArgumentGiven
from mozapkpublisher.common.store import GooglePlayEdit
from mozapkpublisher.common.utils import add_push_arguments, metadata_by_package_name

logger = logging.getLogger(__name__)


def push_aab(
    aabs,
    username,
    secret,
    track,
    rollout_percentage=None,
    dry_run=True,
    contact_server=True,
):
    """
    Args:
        aabs: list of AAB files
        username (str): Google Play service account
        secret (str): Filename of Google Play Credentials file
        track (str): Google Play track to deploy to (e.g.: "nightly"). If "rollout" is chosen,
            the parameter `rollout_percentage` must be specified as well
        rollout_percentage (int): percentage of users to roll out this update to. Must be a number
            in (0-100]. This option is only valid if `track` is set to "rollout"
        dry_run (bool): `True` to do a dry-run
        contact_server (bool): `False` to avoid communicating with the Google Play server.
            Useful if you're using mock credentials.
    """
    if track is None:
        # The Google store allows multiple stability "tracks" to exist for a single app, so it
        # requires you to disambiguate which track you'd like to publish to.
        raise WrongArgumentGiven('The track must be provided')

    # We want to tune down some logs, even when push_aab() isn't called from the command line
    main_logging.init()

    aabs_metadata_per_paths = extract_aabs_metadata(aabs)

    update_aab_kwargs = {
        kwarg_name: kwarg_value
        for kwarg_name, kwarg_value in (
            ('track', track),
            ('rollout_percentage', rollout_percentage)
        )
        if kwarg_value
    }

    # Each distinct product must be uploaded in different "edit"/transaction, so we split them
    # by package name here.
    aabs_by_package_name = metadata_by_package_name(aabs_metadata_per_paths)
    for package_name, extracted_aabs in aabs_by_package_name.items():
        with GooglePlayEdit.transaction(username, secret, package_name, contact_server=contact_server,
                               dry_run=dry_run) as edit:
            edit.update_aab(extracted_aabs, **update_aab_kwargs)


def main():
    parser = argparse.ArgumentParser(description='Upload AABs on the Google Play Store.')

    # TODO: move these to add_push_arguments when Amazon support is removed
    parser.add_argument('track', help='Track on which to upload')
    parser.add_argument(
        '--rollout-percentage',
        type=int,
        choices=range(0, 101),
        metavar='[0-100]',
        default=None,
        help='The percentage of users who will get the update. Specify only if track is rollout'
    )
    parser.add_argument('--commit', action='store_false', dest='dry_run',
                               help='Commit new release on Google Play. This action cannot be '
                                    'reverted')

    add_push_arguments(parser)
    add_aab_checks_arguments(parser)
    config = parser.parse_args()

    track = config.track
    rollout_percentage = config.rollout_percentage

    try:
        push_aab(
            config.aabs,
            config.username,
            config.secret,
            track,
            rollout_percentage,
            config.dry_run,
            config.contact_server,
        )
    except WrongArgumentGiven as e:
        parser.error(e)


__name__ == '__main__' and main()
