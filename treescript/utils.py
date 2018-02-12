"""Treescript general utility functions."""
import asyncio
from asyncio.subprocess import PIPE, STDOUT
import json
import logging
import os

from treescript.exceptions import TaskVerificationError, FailedSubprocess

log = logging.getLogger(__name__)

VALID_ACTIONS = ("tagging", "version_bump")


# mkdir {{{1
def mkdir(path):
    """Equivalent to `mkdir -p`.

    Args:
        path (str): the path to mkdir

    """
    try:
        os.makedirs(path)
        log.info("mkdir {}".format(path))
    except OSError:
        pass


# load_json {{{1
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


# log_output {{{1
async def log_output(fh):
    """Log the output from an async generator.

    Args:
        fh (async generator): the async generator to log output from

    """
    while True:
        line = await fh.readline()
        if line:
            log.info(line.decode("utf-8").rstrip())
        else:
            break


# execute_subprocess {{{1
async def execute_subprocess(command, **kwargs):
    """Execute a command in a subprocess.

    Args:
        command (list): the command to run
        **kwargs: the kwargs to pass to subprocess

    Raises:
        FailedSubprocess: on failure

    """
    message = 'Running "{}"'.format(' '.join(command))
    if 'cwd' in kwargs:
        message += " in {}".format(kwargs['cwd'])
    log.info(message)
    subprocess = await asyncio.create_subprocess_exec(
        *command, stdout=PIPE, stderr=STDOUT, **kwargs
    )
    log.info("COMMAND OUTPUT: ")
    await log_output(subprocess.stdout)
    exitcode = await subprocess.wait()
    log.info("exitcode {}".format(exitcode))

    if exitcode != 0:
        raise FailedSubprocess('Command `{}` failed'.format(' '.join(command)))
