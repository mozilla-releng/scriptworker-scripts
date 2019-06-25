#!/usr/bin/env python
"""iScript: Apple signing and notarization."""
import logging
import os

from scriptworker_client.client import sync_main
from scriptworker_client.utils import run_command
from iscript.exceptions import IScriptError
from iscript.mac import (
    notarize_behavior,
    pkg_behavior,
    sign_behavior,
    sign_and_pkg_behavior,
)
from iscript.util import get_key_config


log = logging.getLogger(__name__)


async def async_main(config, task):
    """Sign all the things.

    Args:
        config (dict): the running config.
        task (dict): the running task.

    """
    await run_command(["hostname"])
    base_key = "mac_config"  # We may support ios_config someday
    key_config = get_key_config(config, task, base_key=base_key)
    behavior = task["payload"].get("behavior", "mac_sign")
    if (
        behavior == "mac_notarize"
        and "mac_notarize" not in key_config["supported_behaviors"]
        and "mac_sign_and_pkg" in key_config["supported_behaviors"]
    ):
        behavior = "mac_sign_and_pkg"
    if behavior not in key_config["supported_behaviors"]:
        raise IScriptError(
            "Unsupported behavior {} given scopes {}!".format(behavior, task["scopes"])
        )
    if behavior == "mac_pkg":
        await pkg_behavior(config, task)
        return
    elif behavior == "mac_notarize":
        await notarize_behavior(config, task)
        return
    elif behavior == "mac_sign":
        await sign_behavior(config, task)
        return
    elif behavior == "mac_sign_and_pkg":
        # For staging releases; or should we mac_notarize but skip notarization
        # for dep?
        await sign_and_pkg_behavior(config, task)
        return
    raise IScriptError("Unknown iscript behavior {}!".format(behavior))


def get_default_config(base_dir=None):
    """Create the default config to work from.

    Args:
        base_dir (str, optional): the directory above the `work_dir` and `artifact_dir`.
            If None, use `..`  Defaults to None.

    Returns:
        dict: the default configuration dict.

    """
    base_dir = base_dir or os.path.dirname(os.getcwd())
    default_config = {
        "work_dir": os.path.join(base_dir, "work"),
        "artifact_dir": os.path.join(base_dir, "artifacts"),
        "schema_file": os.path.join(
            os.path.dirname(__file__), "data", "i_task_schema.json"
        ),
        "local_notarization_accounts": [],
    }
    return default_config


def main():
    """Start signing script."""
    return sync_main(async_main, default_config=get_default_config())


__name__ == "__main__" and main()
