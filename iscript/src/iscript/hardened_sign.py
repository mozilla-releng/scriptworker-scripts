#!/usr/bin/env python
"""Functions to sign packages with hardened runtime"""

import asyncio
import logging
import os
import shutil
from glob import glob
from pathlib import Path
from shutil import copy2

from iscript.autograph import sign_langpacks
from iscript.exceptions import IScriptError
from iscript.mac import (
    copy_pkgs_to_artifact_dir,
    create_pkg_files,
    download_requirements_plist_file,
    extract_all_apps,
    get_app_paths,
    get_langpack_format,
    set_app_path_and_name,
    sign_omnija_with_autograph,
    sign_widevine_dir,
    tar_apps,
    unlock_keychain,
    update_keychain_search_path,
)
from iscript.util import get_sign_config
from scriptworker_client.aio import download_file, raise_future_exceptions, retry_async
from scriptworker_client.exceptions import DownloadError
from scriptworker_client.utils import run_command

log = logging.getLogger(__name__)


async def download_signing_resources(hardened_sign_config, folder: Path):
    """Caches all external resources needed for a signing task"""
    # Get unique entitlement/libconstraint urls
    resource_urls = set()

    # Collect urls from config
    for resource_key in ("entitlements", "libconstraints"):
        for cfg in hardened_sign_config:
            if not cfg.get(resource_key, None):
                continue
            resource_urls.add(cfg[resource_key])

    # Async download and set url -> file location mapping
    url_map = {}
    futures = []
    file_counter = 0
    for url in resource_urls:
        filename = url.split("/")[-1]
        # Prevent overwriting files with same name
        dest = folder / f"{file_counter}-{filename}"
        file_counter += 1
        assert not dest.exists(), f"File {dest} already exists, cannot overwrite"
        url_map[url] = dest
        log.info(f"Downloading resource: {filename} from {url}")
        futures.append(
            asyncio.ensure_future(
                retry_async(
                    download_file,
                    retry_exceptions=(DownloadError, TimeoutError),
                    args=(url, dest),
                    attempts=5,
                )
            )
        )
    await raise_future_exceptions(futures)
    # Return map of url to file location
    return url_map


def check_globs(app_path, globs):
    for path_glob in globs:
        separator = ""
        if not path_glob.startswith("/"):
            separator = "/"
        joined_path = str(app_path) + separator + path_glob
        binary_paths = glob(joined_path, recursive=True)
        if len(binary_paths) == 0:
            log.warning('file pattern "%s" matches no files' % joined_path)


def copy_provisioning_profile(pprofile, app_path, config):
    # TODO: Eventually move this to script_config
    pprofile_source_dir = Path(config["work_dir"]).parent / "provisionprofiles"

    # Check if file exists locally
    source_file = Path(pprofile_source_dir / pprofile["profile_name"]).resolve()
    try:
        source_file.relative_to(pprofile_source_dir)
    except ValueError:
        raise IScriptError("Illegal directory traversal resolving provisioning profile source")
    if not source_file.is_file():
        raise IScriptError(f"Provisioning profile not found in worker: {pprofile['profile_name']}")

    # Adding ./ to destination as workaround for destination starting with /
    destination = Path(Path(app_path) / ("./" + pprofile["target_path"])).resolve()
    # If provided destination is a directory, then use default filename for profiles
    if destination.is_dir():
        destination = destination / "embedded.provisionprofile"
    try:
        destination.relative_to(app_path)
    except ValueError:
        raise IScriptError("Illegal directory traversal resolving provisioning profile destination")
    # If profile already exists in app, then replace
    if destination.exists():
        log.warn(f"Profile already exist. Replacing {str(destination)}")
    copy2(source_file, destination)
    log.debug(f"Copied {source_file} to {destination}")


def build_sign_command(app_path, identity, keychain, config, file_map):
    cmd = [
        "codesign",
        "--verbose",
        "--sign",
        identity,
        "--keychain",
        keychain,
    ]
    # Flag options
    for option in ("deep", "force"):
        if config.get(option):
            cmd.append(f"--{option}")
    # Requirements
    if config.get("requirements"):
        cmd.append("--requirements")
        cmd.append(config["requirements"])
    # Explicit codesign identifier
    if config.get("identifier"):
        cmd.append("--identifier")
        cmd.append(config["identifier"])
    # --options
    if config.get("runtime"):
        cmd.append("--options")
        cmd.append("runtime")
    # Library constraints
    if config.get("libconstraints"):
        cmd.append("--enforce-constraint-validity")
        cmd.append("--library-constraint")
        cmd.append(file_map[config["libconstraints"]])
    # Entitlements
    if config.get("entitlements"):
        cmd.append("--entitlements")
        cmd.append(file_map[config["entitlements"]])
    # List globs
    for path_glob in config["globs"]:
        separator = ""
        if not path_glob.startswith("/"):
            separator = "/"
        # Join incoming glob with root of app path
        full_path_glob = str(app_path) + separator + path_glob
        for binary_path in glob(full_path_glob, recursive=True):
            cmd.append(binary_path)
    return cmd


async def sign_hardened_behavior(config, task, create_pkg=False, **kwargs):
    """Sign all mac apps for this task with hardened runtime

    Args:
        config (dict): the running configuration
        task (dict): the running task
        create_pkg (bool): if it should create pkg installer for each app

    Raises:
        IScriptError: on fatal error.
    """
    sign_config = get_sign_config(config, task, base_key="mac_config")

    # Setup folder for downloaded files
    tempdir = Path(config["work_dir"]) / "tmp_resources"
    if tempdir.exists():
        shutil.rmtree(tempdir, ignore_errors=True)
    os.mkdir(tempdir)

    hardened_sign_config = task["payload"]["hardened-sign-config"]
    sign_config_files = await download_signing_resources(hardened_sign_config, tempdir)

    non_langpack_apps = []
    for app in get_app_paths(config, task):
        if fmt := get_langpack_format(app):
            await sign_langpacks(config, sign_config, [app], fmt)
        else:
            non_langpack_apps.append(app)
    await extract_all_apps(config, non_langpack_apps)
    await unlock_keychain(sign_config["signing_keychain"], sign_config["keychain_password"])
    await update_keychain_search_path(config, sign_config["signing_keychain"])
    for app in non_langpack_apps:
        set_app_path_and_name(app)

    # sign omni.ja
    futures = []
    for app in non_langpack_apps:
        fmt = next((f for f in app.formats if "omnija" in f), None)
        if fmt:
            futures.append(asyncio.ensure_future(sign_omnija_with_autograph(config, sign_config, app.app_path, fmt)))
    await raise_future_exceptions(futures)

    # sign widevine
    futures = []
    for app in non_langpack_apps:
        fmt = next((f for f in app.formats if "widevine" in f), None)
        if fmt:
            futures.append(asyncio.ensure_future(sign_widevine_dir(config, sign_config, app.app_path, fmt)))
    await raise_future_exceptions(futures)
    await unlock_keychain(sign_config["signing_keychain"], sign_config["keychain_password"])
    futures = []

    # Handle provisioning profile if provided
    pprofile_configs = task["payload"].get("provisioning-profile-config", [])
    for pprofile in pprofile_configs:
        copy_provisioning_profile(pprofile, app.app_path, config)

    # sign apps concurrently
    for app in non_langpack_apps:
        for config_settings in hardened_sign_config:
            check_globs(app.app_path, config_settings["globs"])
            command = build_sign_command(
                app_path=app.app_path,
                identity=sign_config["identity"],
                keychain=sign_config["signing_keychain"],
                config=config_settings,
                file_map=sign_config_files,
            )
            await run_command(
                command,
                cwd=app.parent_dir,
                exception=IScriptError,
            )

    await tar_apps(config, non_langpack_apps)
    log.info("Done signing apps.")

    if create_pkg:
        requirements_plist_path = await download_requirements_plist_file(config, task)
        await create_pkg_files(config, sign_config, non_langpack_apps, requirements_plist_path)
        await copy_pkgs_to_artifact_dir(config, non_langpack_apps)
        log.info("Done creating pkgs.")

    return non_langpack_apps
