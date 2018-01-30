"""Treescript general utility functions."""
# import asyncio
# from asyncio.subprocess import PIPE, STDOUT
# import functools
# import hashlib
import json
import logging
# import os
# from shutil import copyfile
# import traceback
# from collections import namedtuple

from treescript.exceptions import TaskVerificationError

log = logging.getLogger(__name__)

VALID_ACTIONS = ("tagging", "versionbump")


def load_json(path):
    """Load json from path.

    Args:
        path (str): the path to read from

    Returns:
        dict: the loaded json object

    """
    with open(path, "r") as fh:
        return json.load(fh)


# task_actions {{{1
def task_action_types(task):
    """Extract task actions as scope definitions.

    Args:
        task (dict): the task definition.

    Raises:
        TaskVerificationError: if the number of cert scopes is not 1.

    Returns:
        str: the cert type.

    """
    valid_action_scopes = tuple(
        "project:releng:treescript:action:{}".format(action) for action in VALID_ACTIONS
    )
    actions = tuple(s for s in task["scopes"] if
                    s.startswith("project:releng:treescript:action:"))
    log.info("Action requests: %s", actions)
    if len(actions) < 1:
        raise TaskVerificationError("Need at least one valid action specified in scopes")
    invalid_actions = set(actions) - set(valid_action_scopes)
    if len(invalid_actions) > 0:
        raise TaskVerificationError("Task specified invalid actions: {}".format(invalid_actions))
    return actions
