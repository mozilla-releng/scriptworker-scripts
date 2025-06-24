#!/usr/bin/env python
"""iscript mac installer package functions."""

import os
import logging

from iscript.exceptions import IScriptError
from scriptworker_client.aio import retry_async
from scriptworker_client.utils import makedirs, run_command
from iscript.mac import (
    App,
    copy_pkgs_to_artifact_dir,
    get_app_paths,
    unlock_keychain,
    update_keychain_search_path,
)
from iscript.util import get_sign_config

log = logging.getLogger(__name__)


async def sign_pkg_behavior(config, task):
    """Sign a macOS installer package

    Args:
        config (dict): the running configuration
        task (dict): the running task

    Raises:
        IScriptError: on fatal error.

    """
    work_dir = config["work_dir"]
    sign_config = get_sign_config(config, task, base_key="mac_config")

    await unlock_keychain(sign_config["signing_keychain"], sign_config["keychain_password"])
    await update_keychain_search_path(config, sign_config["signing_keychain"])

    if "pkg_cert_id" not in sign_config:
        raise IScriptError("Unable to find installer signing cert!")

    sign_cmd = ["productsign", "--keychain", sign_config["signing_keychain"], "--sign", sign_config["pkg_cert_id"]]
    signed_apps = []
    counter = 1
    for app in get_app_paths(config, task):
        if not app.orig_path.endswith(".pkg"):
            log.info("Unable to sign: unexpected file extension")
            continue

        app.parent_dir = os.path.dirname(app.orig_path)
        app.pkg_path = os.path.join(work_dir, f"productsign-{counter}", os.path.basename(app.orig_path))
        makedirs(os.path.dirname(app.pkg_path))
        await retry_async(
            run_command,
            args=[sign_cmd + [app.orig_path, app.pkg_path]],
            kwargs={"cwd": work_dir, "exception": IScriptError, "output_log_on_exception": True},
            retry_exceptions=(IScriptError,),
        )

        counter = counter + 1
        signed_apps.append(app)

    await copy_pkgs_to_artifact_dir(config, signed_apps)
