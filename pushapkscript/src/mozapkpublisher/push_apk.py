#!/usr/bin/env python3

import asyncio
import argparse
import logging

from mozapkpublisher.common import main_logging
from mozapkpublisher.common.apk import add_apk_checks_arguments, extract_and_check_apks_metadata
from mozapkpublisher.common.store import GooglePlayEdit
from mozapkpublisher.common.utils import add_push_arguments, metadata_by_package_name, check_push_arguments
from mozapkpublisher.common.exceptions import WrongArgumentGiven
from mozapkpublisher.sgs_api import SamsungGalaxyStore

logger = logging.getLogger(__name__)


async def push_apk(
    apks,
    secret,
    expected_package_names,
    track,
    store="google",
    rollout_percentage=None,
    dry_run=True,
    contact_server=True,
    skip_check_ordered_version_codes=False,
    skip_check_multiple_locales=False,
    skip_check_same_locales=False,
    skip_checks_fennec=False,
    *,
    submit=False,
    sgs_service_account_id=None,
    sgs_access_token=None,
):
    """
    Args:
        apks: list of APK files
        secret (str): Filename of Google Play Credentials file (json)
        expected_package_names (list of str): defines what the expected package names must be.
        track (str): Google Play track to deploy to (e.g.: "nightly"). If "rollout" is chosen, the parameter
            `rollout_percentage` must be specified as well
        rollout_percentage (int): percentage of users to roll out this update to. Must be a number in (0-100]. This
            option is only valid if `track` is set to "rollout"
        dry_run (bool): `True` to do a dry-run
        contact_server (bool): `False` to avoid communicating with the Google Play server. Useful if you're using mock
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

    # Each distinct product must be uploaded in different "edit"/transaction, so we split them
    # by package name here.
    apks_by_package_name = metadata_by_package_name(apks_metadata_per_paths)

    if store == "google":
        update_app_kwargs = {
            kwarg_name: kwarg_value
            for kwarg_name, kwarg_value in (
                ('track', track),
                ('rollout_percentage', rollout_percentage)
            )
            if kwarg_value
        }

        for package_name, extracted_apks in apks_by_package_name.items():
            with GooglePlayEdit.transaction(secret, package_name, contact_server=contact_server,
                                            dry_run=dry_run) as edit:
                edit.update_app(extracted_apks, **update_app_kwargs)
    elif store == "samsung":
        if not (sgs_service_account_id and sgs_access_token):
            raise RuntimeError("You must provided an account id and access token for the samsung galaxy store")

        async with SamsungGalaxyStore(sgs_service_account_id, sgs_access_token, dry_run=dry_run) as sgs:
            for package_name, apks in apks_by_package_name.items():
                await sgs.upload_apks(package_name, apks, rollout_percentage, submit=submit)
    else:
        raise WrongArgumentGiven("Unkown target store: {}".format(store))


def main():
    parser = argparse.ArgumentParser(description='Upload APKs on the Google Play Store.')
    add_push_arguments(parser)
    add_apk_checks_arguments(parser)
    config = parser.parse_args()
    check_push_arguments(parser, config)

    asyncio.run(push_apk(
        config.apks,
        config.secret,
        config.expected_package_names,
        config.track,
        config.store,
        config.rollout_percentage,
        config.dry_run,
        config.contact_server,
        config.skip_check_ordered_version_codes,
        config.skip_check_multiple_locales,
        config.skip_check_same_locales,
        config.skip_checks_fennec,
        submit=config.submit,
        sgs_service_account_id=config.sgs_service_account_id,
        sgs_access_token=config.sgs_access_token,
    ))


__name__ == '__main__' and main()
