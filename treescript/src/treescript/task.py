#!/usr/bin/env python
"""Treescript task functions."""
import logging

from treescript.exceptions import TaskVerificationError

log = logging.getLogger(__name__)


# This list should be sorted in the order the actions should be taken
# XXX remove `tagging` when we remove scope support for actions
#     (payload-based actions will use `tag`)
VALID_ACTIONS = ("tag", "tagging", "version_bump", "l10n_bump", "push", "merge_day")

DONTBUILD_MSG = " DONTBUILD"
CLOSED_TREE_MSG = " CLOSED TREE"


def _sort_actions(actions):
    return sorted(actions, key=VALID_ACTIONS.index)


# get_source_repo {{{1
def get_metadata_source_repo(task):
    """Get the source repo from the task metadata.

    Assumes `task['metadata']['source']` exists and is a link to a mercurial file on
    hg.mozilla.org (over https)

    Args:
        task: the task definition.

    Returns:
        str: url, including https scheme, to mercurial repository of the source repo.

    Raises:
        TaskVerificationError: on unexpected input.

    """
    source = task.get("metadata", {}).get("source", None)
    if not source:
        raise TaskVerificationError("No source, how did that happen")
    if not source.startswith("https://hg.mozilla.org/"):
        raise TaskVerificationError(
            "Unable to operate on sources not in hg.mozilla.org"
        )
    parts = source.split("/file/")
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
        str: url, including https scheme, to mercurial repository of the source repo.

    Raises:
        TaskVerificationError: on unexpected input.

    """
    if task["payload"].get("source_repo"):
        return task["payload"]["source_repo"]
    return get_metadata_source_repo(task)


def get_short_source_repo(task):
    """Get the name of the source repo, e.g. mozilla-central.

    Args:
        task: the task definition.

    Returns:
        str: the name of the source repo

    """
    source_repo = get_source_repo(task)
    parts = source_repo.split("/")
    return parts[-1]


# get_branch {{{1
def get_branch(task, default=None):
    """Get the optional branch from the task payload.

    This is largely for relbranch support in mercurial.

    Args:
        task (dict): the running task

    Returns:
        None: if no branch specified
        str: the branch specified in the task

    """
    return task.get("payload", {}).get("branch", default)


# get_tag_info {{{1
def get_tag_info(task):
    """Get the tag information from the task metadata.

    Assumes task['payload']['tag_info'] exists and is in the proper format.

    Args:
        task: the task definition.

    Returns:
        object: the tag info structure as passed to the task payload.

    Raises:
        TaskVerificationError: If run without tag_info in task definition.

    """
    tag_info = task.get("payload", {}).get("tag_info")
    if not tag_info:
        raise TaskVerificationError("Requested tagging but no tag_info in payload")
    return tag_info


# get_version_bump_info {{{1
def get_version_bump_info(task):
    """Get the version bump information from the task metadata.

    Args:
        task: the task definition.

    Returns:
        object: the tag info structure as passed to the task payload.

    Raises:
        TaskVerificationError: If run without tag_info in task definition.

    """
    version_info = task.get("payload", {}).get("version_bump_info")
    if not version_info:
        raise TaskVerificationError(
            "Requested version bump but no version_bump_info in payload"
        )
    return version_info


# get_l10n_bump_info {{{1
def get_l10n_bump_info(task):
    """Get the l10n bump information from the task metadata.

    Args:
        task: the task definition.

    Returns:
        object: the tag info structure as passed to the task payload.

    Raises:
        TaskVerificationError: If run without tag_info in task definition.

    """
    l10n_bump_info = task.get("payload", {}).get("l10n_bump_info")
    if not l10n_bump_info:
        raise TaskVerificationError(
            "Requested l10n bump but no l10n_bump_info in payload"
        )
    return l10n_bump_info


# get dontbuild {{{1
def get_dontbuild(task):
    """Get information on whether DONTBUILD needs to be attached at the end of commit message.

    Args:
        task: the task definition.

    Returns:
        boolean: the dontbuild info as passed to the task payload (defaulted to false).

    """
    return task.get("payload", {}).get("dontbuild", False)


# get_ignore_closed_tree {{{1
def get_ignore_closed_tree(task):
    """Get information on whether CLOSED TREE needs to be added to the commit message.

    Args:
        task: the task definition.

    Returns:
        boolean: the ``ignore_closed_tree`` info as passed to the task payload (defaulted to false).

    """
    return task.get("payload", {}).get("ignore_closed_tree", False)


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
    if task.get("payload", {}).get("actions"):
        actions = task["payload"]["actions"]
    else:
        log.warning(
            "Scopes-based actions are deprecated! Use task.payload.actions instead."
        )
        actions = [
            s.split(":")[-1]
            for s in task["scopes"]
            if s.startswith(config["taskcluster_scope_prefix"] + "action:")
        ]
        if len(actions) < 1:
            raise TaskVerificationError(
                "Need at least one valid action specified in scopes"
            )
    log.info("Action requests: %s", actions)
    invalid_actions = set(actions) - set(VALID_ACTIONS)
    if len(invalid_actions) > 0:
        raise TaskVerificationError(
            "Task specified invalid actions: {}".format(invalid_actions)
        )

    return _sort_actions(actions)


# is_dry_run {{{1
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


# get_merge_flavor {{{1
def get_merge_flavor(task):
    """Get the type of repo merge to perform.

    Args:
        task: the task definition.

    Returns:
        str: the ``merge_day -> flavor`` info as passed to the task payload.

    """
    return task.get("payload", {}).get("merge_info", dict()).get("flavor")
