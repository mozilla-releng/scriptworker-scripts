#!/usr/bin/env python
"""Treescript task functions."""

import logging

from treescript.exceptions import TaskVerificationError

log = logging.getLogger(__name__)


# These sets should be listed in the order the actions should be taken for
# human reference.
VALID_ACTIONS = {
    "mobile": {"version_bump", "create_branch"},
}

DONTBUILD_MSG = " DONTBUILD"


# get_source_repo {{{1
def get_metadata_source_repo(task):
    """Get the source repo from the task metadata.

    Assumes `task['metadata']['source']` exists and is a link to a file on
    github.com

    Args:
        task: the task definition.

    Returns:
        str: url, including https scheme, to the source repo.

    Raises:
        TaskVerificationError: on unexpected input.

    """
    source = task.get("metadata", {}).get("source", None)
    if not source:
        raise TaskVerificationError("No source, how did that happen")
    if not source.startswith("https://github.com/"):
        raise TaskVerificationError("Unable to operate on sources not in github.com")
    parts = source.split("/blob/")

    if len(parts) < 2:
        raise TaskVerificationError("Source url is in unexpected format")

    return parts[0]


def get_source_repo(task):
    """Get the source repo from the task payload, falling back to the metadata.

    First looks for `task['payload']['source_repo']`, then falls back to
    ``get_metadata_source_repo``.

    Args:
        task: the task definition.

    Returns:
        str: url, including https scheme, to the source repo.

    Raises:
        TaskVerificationError: on unexpected input.

    """
    if task["payload"].get("source_repo"):
        return task["payload"]["source_repo"]
    return get_metadata_source_repo(task)


def get_short_source_repo(task):
    """Get the name of the source repo, e.g. firefox-ios.

    Args:
        task: the task definition.

    Returns:
        str: the name of the source repo

    """
    source_repo = get_source_repo(task)
    parts = source_repo.split("/")
    return parts[-1]


_GIT_REF_HEADS = "refs/heads/"


# get_branch {{{1
def get_branch(task, default=None):
    """Get the optional branch from the task payload.

    Args:
        task (dict): the running task

    Returns:
        None: if no branch specified
        str: the branch specified in the task

    """
    branch = task.get("payload", {}).get("branch", default)
    if branch and branch.startswith(_GIT_REF_HEADS):
        branch = branch[len(_GIT_REF_HEADS) :]
    return branch


# get_version_bump_info {{{1
def get_version_bump_info(task):
    """Get the version bump information from the task metadata.

    Args:
        task: the task definition.

    Returns:
        object: the info structure as passed to the task payload.

    Raises:
        TaskVerificationError: If expected item missing from task definition.

    """
    version_info = task.get("payload", {}).get("version_bump_info")
    if not version_info:
        raise TaskVerificationError("Requested version bump but no version_bump_info in payload")
    return version_info


# get_create_branch_info {{{1
def get_create_branch_info(task):
    """Get the create branch information from the task metadata.

    Args:
        task: the task definition.

    Returns:
        object: the info structure as passed to the task payload.

    Raises:
        TaskVerificationError: If expected item missing from task definition.

    """
    create_branch_info = task.get("payload", {}).get("create_branch_info")
    if not create_branch_info:
        raise TaskVerificationError("Requested create branch but no create_branch_info in payload")
    return create_branch_info


# get dontbuild {{{1
def get_dontbuild(task):
    """Get information on whether DONTBUILD needs to be attached at the end of commit message.

    Args:
        task: the task definition.

    Returns:
        boolean: the dontbuild info as passed to the task payload (defaulted to false).

    """
    return task.get("payload", {}).get("dontbuild", False)


# task_action_types {{{1
def task_action_types(config, task):
    """Extract task actions from task payload.

    Args:
        config (dict): the running config.
        task (dict): the task definition.

    Raises:
        TaskVerificationError: if unknown actions are specified.

    Returns:
        set: the set of specified actions

    """
    # Actions derived from scopes
    repo = get_short_source_repo(task)
    prefix = f"project:{config['trust_domain']}:{repo}:treescript:action:"
    actions = set([s[len(prefix) :] for s in task["scopes"] if s.startswith(prefix)])

    if not actions:
        scope_str = "\n  ".join(sorted(task["scopes"]))
        raise TaskVerificationError(f"No action scopes match '{prefix[:-1]}':\n  {scope_str}")

    log.info(f"Action requests: {actions}")
    log.info(f"Valid actions: {VALID_ACTIONS[config['trust_domain']]}")
    invalid_actions = actions - VALID_ACTIONS[config["trust_domain"]]
    if len(invalid_actions) > 0:
        raise TaskVerificationError(f"Task specified invalid actions for '{config['trust_domain']}: {invalid_actions}")

    return actions


# is_dry_run {{{1
def should_push(task):
    """Determine whether this task should push the changes it makes.

    If `dry_run` is true on the task, there will not be a push.
    Otherwise, there will be a push.

    Args:
        task (dict): the task definition.

    Returns:
        bool: whether this task should push

    """
    dry_run = task["payload"].get("dry_run", False)
    if dry_run:
        log.info("Not pushing changes, dry_run was forced")
    return not dry_run
