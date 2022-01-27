#!/usr/bin/env python
"""Mac VPN notarization behavior."""

import logging
import os

from scriptworker_client.utils import run_command

from iscript.exceptions import IScriptError
from iscript.mac import (
    App,
    copy_pkgs_to_artifact_dir,
    create_pkg_files,
    download_entitlements_file,
    download_provisioning_profile,
    extract_all_apps,
    get_app_paths,
    notarize_no_sudo,
    poll_all_notarization_status,
    sign_all_apps,
    staple_notarization,
    unlock_keychain,
    update_keychain_search_path,
)
from iscript.util import get_sign_config

log = logging.getLogger(__name__)

# TODO: Move provisioning profiles from braindump
LOGINITEM_PROVISIONING_PROFILE = "https://hg.mozilla.org/build/braindump/raw-file/tip/signing-related/firefoxvpn_loginitem_developerid.provisionprofile"
NATIVEMESSAGING_PROVISIONING_PROFILE = "https://hg.mozilla.org/build/braindump/raw-file/tip/signing-related/FirefoxVPN_Native_Messaging.provisionprofile"
MOZILLA_VPN_PROVISIONING_PROFILE = "https://hg.mozilla.org/build/braindump/raw-file/tip/signing-related/firefoxvpn_developerid.provisionprofile"


async def _create_notarization_zipfile(work_dir, source, dest):
    """Create a zipfile for notarization.

    Keeps parent directory in zip

    Args:
        work_dir (str): base directory from the zip command perspective
        source (str): the source directory/file
        dest (str): destination package

    Raises:
        IScriptError: on failure

    Returns:
        str: the zip path
    """
    await run_command(
        ["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", source, dest],
        cwd=work_dir,
        exception=IScriptError,
    )


async def _sign_app(config, sign_config, app, entitlements_url, provisioning_profile_url):
    """Sign an app.

    Args:
        config (dict): script config
        task (dict): running task
        sign_config (dict): the config for this signing key
        app (App): the App the notarize
        entitlements_url (str): URL for entitlements file
        provisioning_profile_url (str): URL for provisioning profile

    """
    # We mock the task for downloading entitlements and provisioning profiles
    entitlements_path = await download_entitlements_file(config, sign_config, {"payload": {"entitlements-url": entitlements_url}})
    provisioning_profile_path = await download_provisioning_profile(config, {"payload": {"provisioning-profile-url": provisioning_profile_url}})

    await sign_all_apps(config, sign_config, entitlements_path, [app], provisioning_profile_path)

    log.info(f"Done signing app {app.app_name}")


async def notarize_vpn_behavior(config, task):
    """Notarize vpn app.

    Workflow:
    . Sign all inner apps
    . Sign main app
    . Notarize main app

    Args:
        config (dict): the running configuration
        task (dict): the running task

    Raises:
        IScriptError: on fatal error.

    """
    top_app = get_app_paths(config, task)
    assert len(top_app) == 1

    await extract_all_apps(config, top_app)

    # Extract fills in app.parent_dir
    top_app = top_app[0]

    ##############
    # TODO: Decide what to do with the incoming package
    # TODO: Remove when we switch to .tar.gz payloads (1/2)
    build_zip_path = os.path.join(top_app.parent_dir, "BUILD.zip")
    await run_command(["unzip", build_zip_path, "-d", top_app.parent_dir])
    os.remove(build_zip_path)

    top_app.app_path = os.path.join(top_app.parent_dir, "Mozilla VPN.app")
    ##############

    sign_config = get_sign_config(config, task, base_key="mac_config")

    # Assuming we only need to unlock and update the keychain once
    await unlock_keychain(sign_config["signing_keychain"], sign_config["keychain_password"])
    await update_keychain_search_path(config, sign_config["signing_keychain"])

    submodule_dir = os.path.join(top_app.parent_dir, "Mozilla VPN.app", "Contents/Library/")

    # LoginItems inner app
    loginitems_app = App(
        orig_path=os.path.join(submodule_dir, "LoginItems/MozillaVPNLoginItem.app"),
        parent_dir=os.path.join(submodule_dir, "LoginItems"),  # Using main app as reference
        app_path=os.path.join(submodule_dir, "LoginItems/MozillaVPNLoginItem.app"),
        app_name="MozillaVPNLoginItem.app",
        formats=task["payload"]["upstreamArtifacts"][0]["formats"],
        artifact_prefix="public/",
    )
    await _sign_app(
        config,
        sign_config,
        loginitems_app,
        entitlements_url=task["payload"]["loginitems-entitlements-url"],
        provisioning_profile_url=LOGINITEM_PROVISIONING_PROFILE,
    )

    # NativeMessaging inner app
    nativemessaging_app = App(
        orig_path=os.path.join(submodule_dir, "NativeMessaging/MozillaVPNNativeMessaging.app"),
        parent_dir=os.path.join(submodule_dir, "NativeMessaging"),  # Using main app as reference
        app_path=os.path.join(submodule_dir, "NativeMessaging/MozillaVPNNativeMessaging.app"),
        app_name="MozillaVPNNativeMessaging.app",
        formats=task["payload"]["upstreamArtifacts"][0]["formats"],
        artifact_prefix="public/",
    )
    await _sign_app(
        config,
        sign_config,
        nativemessaging_app,
        entitlements_url=task["payload"]["nativemessaging-entitlements-url"],
        provisioning_profile_url=NATIVEMESSAGING_PROVISIONING_PROFILE,
    )

    # Main VPN app
    # Already defined from extract - just need the extra bits
    top_app.app_name = "Mozilla VPN.app"
    top_app.formats = task["payload"]["upstreamArtifacts"][0]["formats"]

    await _sign_app(
        config,
        sign_config,
        top_app,
        entitlements_url=task["payload"]["entitlements-url"],
        provisioning_profile_url=MOZILLA_VPN_PROVISIONING_PROFILE,
    )

    # Create the PKG and sign it
    await create_pkg_files(config, sign_config, [top_app])

    # Need to zip the pkg instead
    # zip_path = await create_one_notarization_zipfile(config["work_dir"], [app], sign_config, path_attrs=['app_path'])
    zip_path = os.path.join(config["work_dir"], "notarization.zip")
    await _create_notarization_zipfile(config["work_dir"], top_app.pkg_path, zip_path)

    poll_uuids = await notarize_no_sudo(config["work_dir"], sign_config, zip_path)
    await poll_all_notarization_status(sign_config, poll_uuids)

    log.info("Done notarizing app")

    # TODO: Remove when we switch to .tar.gz payloads (2/2)
    # Fake source so we can create artifact destination path properly
    top_app.orig_path = top_app.orig_path.replace(".zip", ".tar.gz")

    # Staple PKG
    await staple_notarization([top_app], path_attr="pkg_path")

    # Move PKG to artifact directory
    await copy_pkgs_to_artifact_dir(config, [top_app])

    log.info("Done")
