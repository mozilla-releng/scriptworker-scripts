"""Treescript general utility functions."""
import asyncio
from asyncio.subprocess import PIPE, STDOUT
import logging
import os

from treescript.exceptions import TaskVerificationError, FailedSubprocess

log = logging.getLogger(__name__)

# This list should be sorted in the order the actions should be taken
VALID_ACTIONS = ("tagging", "version_bump", "push")

DONTBUILD_MSG = " DONTBUILD"


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


def _sort_actions(actions):
    return sorted(actions, key=VALID_ACTIONS.index)


# task_actions {{{1
def task_action_types(task, script_config):
    """Extract task actions as scope definitions.

    Args:
        task (dict): the task definition.
        script_config (dict): the script configuration

    Raises:
        TaskVerificationError: if the number of cert scopes is not 1.

    Returns:
        str: the cert type.

    """
    actions = [s.split(":")[-1] for s in task["scopes"] if
               s.startswith(script_config["taskcluster_scope_prefix"] + "action:")]
    log.info("Action requests: %s", actions)
    if len(actions) < 1:
        raise TaskVerificationError("Need at least one valid action specified in scopes")
    invalid_actions = set(actions) - set(VALID_ACTIONS)
    if len(invalid_actions) > 0:
        raise TaskVerificationError("Task specified invalid actions: {}".format(invalid_actions))

    return _sort_actions(actions)


# task_actions {{{1
def is_dry_run(task):
    """Extract task force_dry_run feature.

    This is meant as a means to do a dry-run even if the task has the push action scope.

    Args:
        task (dict): the task definition.

    Raises:
        TaskVerificationError: if the number of cert scopes is not 1.

    Returns:
        str: the cert type.

    """
    dry_run = task.get("payload", {}).get("dry_run", False)
    return dry_run


# process_output {{{1
async def process_output(fh):
    """Log the output from an async generator.

    Args:
        fh (async generator): the async generator to log output from

    """
    output = []
    while True:
        line = await fh.readline()
        if line:
            line = line.decode("utf-8").rstrip()
            log.info(line)
            output.append(line)
        else:
            break
    return output


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
    output = await process_output(subprocess.stdout)
    exitcode = await subprocess.wait()
    log.info("exitcode {}".format(exitcode))

    if exitcode != 0:
        raise FailedSubprocess('Command `{}` failed'.format(' '.join(command)))
    return output
