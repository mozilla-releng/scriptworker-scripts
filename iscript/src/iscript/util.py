#!/usr/bin/env python
"""Shared functions for iScript.

Attributes:
    log (logging.Logger): the log object for the module

"""
import logging

from iscript.exceptions import IScriptError

log = logging.getLogger(__name__)

_SCOPES_TO_KEY_CONFIG = {
    "cert:dep-signing": "dep",
    "cert:nightly-signing": "nightly",
    "cert:release-signing": "release",
}


def get_key_config(config, task, base_key="mac_config"):
    """Sanity check the task scopes and return the appropriate ``key_config``.

    The ``key_config`` is, e.g. the ``config.mac_config.dep`` dictionary,
    for mac dep-signing.

    Args:
        config (dict): the running config
        task (dict): the running task
        base_key (str, optional): the base key in the dictionary. Defaults to
            ``mac_config``.

    Raises:
        IScriptError: on failure to verify the scopes.

    Returns:
        dict: the ``key_config``

    """
    try:
        scopes = task["scopes"]
        if len(scopes) != 1:
            raise IScriptError("Illegal number of scopes! {}".format(scopes))
        prefix = config["taskcluster_scope_prefix"]
        scope = scopes[0].replace(prefix, "")
        return config[base_key][_SCOPES_TO_KEY_CONFIG[scope]]
    except KeyError as exc:
        raise IScriptError("get_key_config error: {}".format(str(exc))) from exc
