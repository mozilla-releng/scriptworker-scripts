"""Treescript general utility functions."""
import logging

from treescript.exceptions import TaskVerificationError

log = logging.getLogger(__name__)

# This list should be sorted in the order the actions should be taken
VALID_ACTIONS = ("tagging", "version_bump", "push")

DONTBUILD_MSG = " DONTBUILD"


def _sort_actions(actions):
    return sorted(actions, key=VALID_ACTIONS.index)


# task_action_types {{{1
def task_action_types(config, task):
    """Extract task actions as scope definitions.

    Args:
        config (dict): the running config.
        task (dict): the task definition.

    Raises:
        TaskVerificationError: if the number of cert scopes is not 1.

    Returns:
        str: the cert type.

    """
    actions = [
        s.split(":")[-1]
        for s in task["scopes"]
        if s.startswith(config["taskcluster_scope_prefix"] + "action:")
    ]
    log.info("Action requests: %s", actions)
    if len(actions) < 1:
        raise TaskVerificationError(
            "Need at least one valid action specified in scopes"
        )
    invalid_actions = set(actions) - set(VALID_ACTIONS)
    if len(invalid_actions) > 0:
        raise TaskVerificationError(
            "Task specified invalid actions: {}".format(invalid_actions)
        )

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
