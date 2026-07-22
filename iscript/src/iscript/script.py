#!/usr/bin/env python
"""iScript: Apple signing."""

import logging
import os

from scriptworker_client.client import sync_main
from scriptworker_client.utils import run_command

from iscript.exceptions import IScriptError
from iscript.hardened_sign import sign_hardened_behavior
from iscript.mac import (
    sign_and_pkg_behavior,
    sign_behavior,
    single_file_behavior,
)
from iscript.macvpn import vpn_behavior
from iscript.pkg import sign_pkg_behavior
from iscript.util import get_sign_config

log = logging.getLogger(__name__)


def check_behavior(task, behavior, supported_behaviors):
    """Check that the behavior is supported for these scopes.

    Args:
        config (dict): the running config
        task (dict): the running task

    Raises:
        IScriptError if behavior is unsupported

    Returns:
        str: the behavior

    """
    if behavior not in supported_behaviors:
        raise IScriptError("Unsupported behavior {} given scopes {}!".format(behavior, task["scopes"]))
    return behavior


def get_behavior_function(behavior):
    """Map a behavior to a function.

    Args:
        behavior (str): signing behavior

    Returns:
        tuple: (func, {args})

    """
    functions = {
        "mac_geckodriver": (single_file_behavior, {}),
        "mac_single_file": (single_file_behavior, {}),
        "mac_sign_and_pkg_vpn": (vpn_behavior, {}),
        "mac_sign": (sign_behavior, {}),
        "mac_sign_and_pkg_hardened": (sign_hardened_behavior, {"create_pkg": True}),
        "mac_sign_hardened": (sign_hardened_behavior, {"create_pkg": False}),
        "mac_sign_and_pkg": (sign_and_pkg_behavior, {}),
        "mac_sign_pkg": (sign_pkg_behavior, {}),
    }
    if behavior not in functions:
        raise IScriptError("iscript behavior {} not implemented!".format(behavior))
    return functions[behavior]


async def async_main(config, task):
    """Sign all the things.

    Args:
        config (dict): the running config.
        task (dict): the running task.

    """
    await run_command(["hostname"])
    base_key = "mac_config"  # We may support ios_config someday
    sign_config = get_sign_config(config, task, base_key=base_key)
    behavior = task["payload"].get("behavior", "mac_sign")

    # Raises if behavior not supported
    behavior = check_behavior(task, behavior, sign_config["supported_behaviors"])
    func, args = get_behavior_function(behavior)
    await func(config, task, **args)


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
        "schema_file": os.path.join(os.path.dirname(__file__), "data", "i_task_schema.json"),
    }
    return default_config


def main():
    """Start signing script."""
    return sync_main(async_main, default_config=get_default_config())


__name__ == "__main__" and main()
