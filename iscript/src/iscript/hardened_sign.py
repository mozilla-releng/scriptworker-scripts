#!/usr/bin/env python
"""Functions to sign packages with hardened runtime"""

import asyncio
import logging
import os
import shutil
from glob import glob
from pathlib import Path

from iscript.autograph import sign_langpacks
from iscript.exceptions import IScriptError
from iscript.mac import (
    create_pkg_files,
    copy_pkgs_to_artifact_dir,
    download_requirements_plist_file,
    extract_all_apps,
    filter_apps,
    get_app_paths,
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


async def download_signing_resources(hardened_sign_config, folder):
    """Caches all external resources needed for a signing task"""
    # Get unique entitlement urls
    entitlement_urls = set()
    for cfg in hardened_sign_config:
        if not cfg.get("entitlements", None):
            continue
        entitlement_urls.add(cfg["entitlements"])
    # Async download and set url -> file location mapping
    url_map = {}
    futures = []
    for url in entitlement_urls:
        filename = url.split("/")[-1]
        dest = folder / filename
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
        if not path_glob.startswith("/"):
            raise IScriptError('ERROR: file pattern "{path_glob}" must start with "/"')
        binary_paths = glob(str(app_path / path_glob), recursive=True)
        if len(binary_paths) == 0:
            log.warning('file pattern "%s" matches no files' % path_glob)


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
    # --options
    if config.get("runtime"):
        cmd.append("--options")
        cmd.append("runtime")
    # Entitlements
    if config.get("entitlements"):
        cmd.append("--entitlements")
        cmd.append(file_map[config["entitlements"]])
    # List globs
    for path_glob in config["globs"]:
        # Join incoming glob with root of app path
        full_path_glob = str(app_path) + path_glob
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

    hardened_sign_config = task["payload"]["signing-config"]
    sign_config_files = await download_signing_resources(hardened_sign_config, tempdir)

    all_apps = get_app_paths(config, task)
    langpack_apps = filter_apps(all_apps, fmt="autograph_langpack")
    if langpack_apps:
        await sign_langpacks(config, sign_config, langpack_apps)
        all_apps = filter_apps(all_apps, fmt="autograph_langpack", inverted=True)
    await extract_all_apps(config, all_apps)
    await unlock_keychain(sign_config["signing_keychain"], sign_config["keychain_password"])
    await update_keychain_search_path(config, sign_config["signing_keychain"])
    for app in all_apps:
        set_app_path_and_name(app)

    # sign omni.ja
    futures = []
    for app in all_apps:
        if {"autograph_omnija", "omnija"} & set(app.formats):
            futures.append(asyncio.ensure_future(sign_omnija_with_autograph(config, sign_config, app.app_path)))
    await raise_future_exceptions(futures)

    # sign widevine
    futures = []
    for app in all_apps:
        if {"autograph_widevine", "widevine"} & set(app.formats):
            futures.append(asyncio.ensure_future(sign_widevine_dir(config, sign_config, app.app_path)))
    await raise_future_exceptions(futures)
    await unlock_keychain(sign_config["signing_keychain"], sign_config["keychain_password"])
    futures = []

    # sign apps concurrently
    for app in all_apps:
        for config_settings in hardened_sign_config:
            check_globs(Path(app.app_path), config_settings["globs"])
            command = build_sign_command(
                app_path=Path(app.app_path),
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

    await tar_apps(config, all_apps)
    log.info("Done signing apps.")

    if create_pkg:
        requirements_plist_path = await download_requirements_plist_file(config, task)
        await create_pkg_files(config, sign_config, all_apps, requirements_plist_path)
        await copy_pkgs_to_artifact_dir(config, all_apps)
        log.info("Done creating pkgs.")
