#!/usr/bin/env python
"""Treescript task functions."""
import logging
import os

from treescript.exceptions import TaskVerificationError, TreeScriptError

log = logging.getLogger(__name__)


# get_local_repo {{{1
def get_local_repo(src, src_type="task"):
    """Get the local repo from the task metadata.

    Args:
        src (str): the repo url or directory
        src_type (str, optional): the type of string ``src`` is.
            Can be "task" or "directory". Defaults to "task"

    Returns:
        str: the local repo directory

    Raises:
        TaskVerificationError: on unexpected input.

    """
    if src_type == "task":
        return os.path.join(get_source_repo(src), "src")
    elif src_type == "directory":
        return os.path.join(src, "src")
    else:
        raise TreeScriptError("Unknown src_type {}".format(src_type))


# get_source_repo {{{1
def get_source_repo(task):
    """Get the source repo from the task metadata.

    Assumes task['metadata']['source'] exists and is a link to a mercurial file on
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


# get_version_bump_info {{1
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


# get dontbuild {{{1
def get_dontbuild(task):
    """Get information on whether DONTBUILD needs to be attached at the end of commit message.

    Args:
        task: the task definition.

    Returns:
        boolean: the dontbuild info as passed to the task payload (defaulted to false).

    """
    return task.get("payload", {}).get("dontbuild")
