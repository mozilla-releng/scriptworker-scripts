#!/usr/bin/env python
"""Mac VPN notarization behavior."""

import logging
import os
import plistlib
from pathlib import Path
from shutil import copy2, copytree

from iscript.exceptions import IScriptError
from iscript.hardened_sign import sign_hardened_behavior
from iscript.mac import (
    App,
    copy_pkgs_to_artifact_dir,
    download_entitlements_file,
    extract_all_apps,
    get_app_paths,
    sign_all_apps,
    unlock_keychain,
    update_keychain_search_path,
)
from iscript.util import get_sign_config
from scriptworker_client.aio import retry_async
from scriptworker_client.utils import run_command

log = logging.getLogger(__name__)


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


async def _sign_app(config, sign_config, app, entitlements_url, provisionprofile_filename):
    """Sign an app.

    Args:
        config (dict): script config
        sign_config (dict): the config for this signing key
        app (App): the App the notarize
        entitlements_url (str): URL for entitlements file
        provisionprofile_filename (str): .provisionprofile filename in <config.provisionprofile_dir>

    """
    # We mock the task for downloading entitlements and provisioning profiles
    entitlements_path = await download_entitlements_file(config, sign_config, {"payload": {"entitlements-url": entitlements_url}})

    provisioning_profile_path = None
    if provisionprofile_filename:
        pp_dir = sign_config.get("provisioning_profile_dir", None)
        if not pp_dir:
            pp_dir = Path(config["work_dir"]).parent / "provisionprofiles"
            log.warning(f"No provisioning_profile_dir in settings, using default {pp_dir}")

        provisioning_profile_path = Path(pp_dir) / provisionprofile_filename
        if not provisioning_profile_path.is_file():
            log.warning(f"Could not find provisioning profile: {provisioning_profile_path}")
            provisioning_profile_path = None
        log.info(f"Using provisioning profile: {provisioning_profile_path}")

    await sign_all_apps(config, sign_config, entitlements_path, [app], provisioning_profile_path)

    log.info(f"Done signing app {app.app_name}")


async def _codesign(sign_config, binary_path):
    """Sign command for VPN util binaries.

    Args:
        sign_config (dict): the task config
        binary_path (str): the binary name
    """
    sign_command = [
        "codesign",
        "--timestamp",
        "-fv",
        "-s",
        sign_config["identity"],
        "--keychain",
        sign_config["signing_keychain"],
        "--options",
        "runtime",
        binary_path,
    ]
    await retry_async(
        run_command,
        args=(sign_command,),
        kwargs={"cwd": os.path.dirname(binary_path), "exception": IScriptError, "output_log_on_exception": True},
        retry_exceptions=(IScriptError,),
    )


async def _create_pkg_plist(root_path, plist_path, **kwargs):
    """Generate the component plist file for a Mac application bundle.

    This runs pkgbuild --analyze to generate a template plist, and then
    updates it with values provided by the kwargs.

    Args:
        root_path (str): Root directory tree to be packaged.
        plist_path (str): File path where the plist should be written.
        kwargs: Values to be set in the component plist.

    Raises:
        IScriptError: on failure
    """
    # Analyze the root to be packaged to generate a template plist.
    await run_command(
        ["pkgbuild", "--analyze", "--root", root_path, plist_path],
        exception=IScriptError,
    )

    # Load the plist file.
    with open(plist_path, "rb") as fp:
        data = plistlib.load(fp)

    # Apply changes.
    for i in range(len(data)):
        data[i].update(kwargs)

    # Write out.
    with open(plist_path, "wb") as fp:
        plistlib.dump(data, fp)


async def _create_pkg_files(config, sign_config, app):
    """Create .pkg installer from the .app file.

    VPN specific behavior:
        pkgbuild: requires identifier, version, script, and root; No component arg.
        productbuild: requires distribution, resources, and package-path; No package arg.

    productbuild are different from gecko

    Args:
        config (dict): the task config
        sign_config (dict): the signing config
        app (App): App object to pkg

    Raises:
        IScriptError: on failure
    """
    log.info("Creating PKG files")

    async def _retry_async_cmd(cmd):
        await retry_async(
            func=run_command,
            kwargs={"cmd": cmd, "cwd": app.parent_dir, "exception": IScriptError},
            retry_exceptions=(IScriptError,),
        )

    # We MUST use the same name as Distribution specifies
    app.pkg_path = os.path.join(app.parent_dir, "MozillaVPN.pkg")

    root_path = os.path.join(config["work_dir"], "tmp1root")
    os.mkdir(root_path)

    copytree(app.app_path, os.path.join(root_path, "Mozilla VPN.app"))

    # Generate the component plist.
    component_plist_path = os.path.join(config["work_dir"], "component.plist")
    await _create_pkg_plist(root_path, component_plist_path, BundleIsRelocatable=False)

    cmd_opts = []
    if sign_config.get("pkg_cert_id"):
        cmd_opts = ["--keychain", sign_config["signing_keychain"], "--sign", sign_config["pkg_cert_id"]]
    pkgbuild_cmd = (
        "pkgbuild",
        *cmd_opts,
        "--install-location",
        "/Applications",
        "--identifier",
        sign_config["base_bundle_id"],
        "--version",
        "2.0",  # TODO: version
        "--scripts",
        os.path.join(app.parent_dir, "scripts"),
        "--root",
        root_path,
        "--component-plist",
        component_plist_path,
        app.pkg_path,
    )

    await _retry_async_cmd(pkgbuild_cmd)

    build_path = app.pkg_path.replace(".pkg", ".productbuild.pkg")
    productbuild_cmd = (
        "productbuild",
        *cmd_opts,
        "--distribution",
        os.path.join(app.parent_dir, "Distribution"),
        "--resources",
        os.path.join(app.parent_dir, "Resources"),
        "--package-path",  # TODO: Docs say cwd is already searched, so may not be needed
        app.parent_dir,
        build_path,
    )
    await _retry_async_cmd(productbuild_cmd)

    # Now that productbuild is finished with it, we need to replace for final signing
    os.remove(app.pkg_path)

    if sign_config.get("pkg_cert_id"):
        productsign_cmd = ("productsign", *cmd_opts, build_path, app.pkg_path)
        await _retry_async_cmd(productsign_cmd)
    else:
        copy2(build_path, app.pkg_path)


async def vpn_legacy_behavior(config, task):
    """Sign the VPN app for this task

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

    top_app.app_path = os.path.join(top_app.parent_dir, "Mozilla VPN.app")
    sign_config = get_sign_config(config, task, base_key="mac_config")

    # Assuming we only need to unlock and update the keychain once
    await unlock_keychain(sign_config["signing_keychain"], sign_config["keychain_password"])
    await update_keychain_search_path(config, sign_config["signing_keychain"])

    submodule_dir = os.path.join(top_app.app_path, "Contents/Library/")

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
        entitlements_url=task["payload"]["loginItemsEntitlementsUrl"],
        provisionprofile_filename="orgmozillamacosFirefoxVPNloginitem.provisionprofile",
    )

    utils_dir = os.path.join(top_app.app_path, "Contents/Resources/utils")
    # Wireguard inner app
    await _codesign(sign_config, os.path.join(utils_dir, "wireguard-go"))
    # Mozillavpnnp
    await _codesign(sign_config, os.path.join(utils_dir, "mozillavpnnp"))

    # Prevent override of entitlements of LoginItems
    sign_config["skip_dirs"] = sign_config.setdefault("skip_dirs", tuple()) + ("LoginItems",)

    # Main VPN app
    # Already defined from extract - just need the extra bits
    top_app.app_name = "Mozilla VPN.app"
    top_app.formats = task["payload"]["upstreamArtifacts"][0]["formats"]

    await _sign_app(
        config,
        sign_config,
        top_app,
        entitlements_url=task["payload"]["entitlementsUrl"],
        provisionprofile_filename="orgmozillamacosFirefoxVPN.provisionprofile",
    )

    return [top_app]


async def vpn_behavior(config, task):
    """Notarize vpn app.

    Workflow:
    . Sign all inner apps
    . Sign main app
    . Create pkg
    . Zip pkg
    . Move zipped app to artifacts

    Args:
        config (dict): the running configuration
        task (dict): the running task
        notarize (bool): if notarization is enabled

    Raises:
        IScriptError: on fatal error.

    """

    # Sign the application bundle(s)
    if "hardened-sign-config" in task["payload"]:
        top_apps = await sign_hardened_behavior(config, task, create_pkg=False)
    else:
        top_apps = await vpn_legacy_behavior(config, task)

    # Create the PKG and sign it
    assert len(top_apps) == 1
    top_app = top_apps[0]
    sign_config = get_sign_config(config, task, base_key="mac_config")
    await _create_pkg_files(config, sign_config, top_app)

    # Move PKG to artifact directory
    await copy_pkgs_to_artifact_dir(config, [top_app])

    log.info("Done")
