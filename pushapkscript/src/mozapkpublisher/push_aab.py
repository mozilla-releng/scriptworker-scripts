#!/usr/bin/env python3

import argparse
import asyncio
import logging

from mozapkpublisher.common import main_logging
from mozapkpublisher.common.aab import add_aab_checks_arguments, extract_aabs_metadata
from mozapkpublisher.common.store import GooglePlayEdit
from mozapkpublisher.common.utils import add_push_arguments, metadata_by_package_name, check_push_arguments

logger = logging.getLogger(__name__)


async def push_aab(
    aabs,
    secret,
    track,
    rollout_percentage=None,
    dry_run=True,
    contact_server=True,
):
    """
    Args:
        aabs: list of AAB files
        secret (str): Filename of Google Play Credentials file (json)
        track (str): Google Play track to deploy to (e.g.: "nightly"). If "rollout" is chosen,
            the parameter `rollout_percentage` must be specified as well
        rollout_percentage (int): percentage of users to roll out this update to. Must be a number
            in (0-100]. This option is only valid if `track` is set to "rollout"
        dry_run (bool): `True` to do a dry-run
        contact_server (bool): `False` to avoid communicating with the Google Play server.
            Useful if you're using mock credentials.
    """
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
        with GooglePlayEdit.transaction(secret, package_name, contact_server=contact_server,
                                        dry_run=dry_run) as edit:
            edit.update_aab(extracted_aabs, **update_aab_kwargs)


def main():
    parser = argparse.ArgumentParser(description='Upload AABs on the Google Play Store.')
    add_push_arguments(parser)
    add_aab_checks_arguments(parser)
    config = parser.parse_args()
    check_push_arguments(parser, config)

    if config.store != "google":
        parser.error("Pushing AABs is only support for the google store")

    asyncio.run(push_aab(
        config.aabs,
        config.secret,
        config.track,
        config.rollout_percentage,
        config.dry_run,
        config.contact_server,
    ))


__name__ == '__main__' and main()
