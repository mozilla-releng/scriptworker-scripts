#!/usr/bin/env python
"""Treescript version manipulation."""

import logging
from difflib import unified_diff
from typing import Dict, List, Tuple, Type

from mozilla_version.mobile import MobileVersion
from mozilla_version.version import BaseVersion

from treescript.exceptions import TaskVerificationError, TreeScriptError
from treescript.github.client import GithubClient
from treescript.util.task import DONTBUILD_MSG, get_branch, get_dontbuild, get_version_bump_info, should_push

log = logging.getLogger(__name__)


ALLOWED_BUMP_FILES = ("version.txt",)

FileContents = Dict[str, str]


_VERSION_CLASS_PER_BEGINNING_OF_PATH = {
    "mobile/android/": MobileVersion,
}

_VERSION_CLASS_PER_END_OF_SOURCE_REPO = {
    "firefox-android": MobileVersion,
}


def _find_what_version_parser_to_use(file_, repo):
    version_classes = [cls for path, cls in _VERSION_CLASS_PER_BEGINNING_OF_PATH.items() if file_.startswith(path)]

    number_of_version_classes = len(version_classes)
    if number_of_version_classes > 1:
        raise TreeScriptError(f'File "{file_}" matched too many classes: {version_classes}')
    if number_of_version_classes > 0:
        return version_classes[0]

    log.info("Could not determine version class based on file path. Falling back to repo")

    version_classes = [cls for repo_name, cls in _VERSION_CLASS_PER_END_OF_SOURCE_REPO.items() if repo.endswith(repo_name)]
    try:
        return version_classes[0]
    except IndexError as exc:
        raise TreeScriptError(exc) from exc


def get_version(contents: str, version_cls: Type[BaseVersion]) -> BaseVersion:
    """Parse the version from file contents.

    Args:
        contents (str): The contents of the version.txt file.
        version_cls (BaseVersion): The `mozilla-version` class to parse the version with.

    Returns:
        BaseVersion: The parsed version object.
    """
    lines = [line for line in contents.splitlines() if line and not line.startswith("#")]
    return version_cls.parse(lines[-1])


async def bump_version(client: GithubClient, task: Dict) -> None:
    """Perform a version bump.

    This function takes its inputs from task by using the ``get_version_bump_info``
    function from treescript.task. Using `next_version` and `files`, then
    calls do_version_bump to perform the work.

    Args:
        client (GithubClient): GithubClient instance for associated repo.
        task (dict): The running task.

    Returns:
        int: the number of commits created.

    """
    branch = get_branch(task)
    bump_info = get_version_bump_info(task)

    log.info(f"Version bumping {branch} branch of {client.owner}/{client.repo} to {bump_info['next_version']}")

    changes, diff = await do_bump_version(client, bump_info["files"], bump_info["next_version"], branch)

    if not changes:
        log.warn("No changes to commit!")
        return

    commit_msg = "Automatic version bump CLOSED TREE NO BUG a=release"
    if get_dontbuild(task):
        commit_msg += DONTBUILD_MSG

    push = should_push(task, [])
    verb = "Committing" if push else "Would commit"
    log.info(f"{verb} the following patch:\n\n{commit_msg}\n{diff}\n")

    if push:
        await client.commit(branch, commit_msg, additions=changes)


async def do_bump_version(client: GithubClient, files: List[str], next_version: str, branch: str) -> Tuple[FileContents, str]:
    """Perform a version bump.

    This function takes its inputs from task by using the ``get_version_bump_info``
    function from treescript.task. Using `next_version` and `files`.

    This function does nothing (but logs) if the current version and next version
    match, and nothing if the next_version is actually less than current_version.

    Args:
        client (GithubClient): The Github client.
        files (List[str]): A list of files that need to be version bumped.
        next_version (str): The version to bump to.
        branch (str): The branch to bump the files on.

    Raises:
        TaskverificationError: if a file specified is not allowed, or
                               if the file is not in the target repository.

    Returns:
        Tuple[FileContents, str]: A tuple of length two. The first item is an
            object mapping file name to new contents. The second is a unified diff
            of the changes made.
    """
    changes = {}
    diff = []
    file_contents = await client.get_files(files, branch=branch)
    for file_ in files:
        if file_ not in ALLOWED_BUMP_FILES:
            raise TaskVerificationError("{} is not in version bump whitelist".format(file_))

        contents = file_contents[file_]

        VersionClass = _find_what_version_parser_to_use(file_, client.repo)
        curver = get_version(contents, VersionClass)
        nextver = VersionClass.parse(next_version)

        if nextver < curver:
            log.warning("Version bumping skipped due to conflicting values: (next version {} is < current version {})".format(nextver, curver))
            continue
        elif nextver == curver:
            log.info("Version bumping skipped due to unchanged values")
            continue
        else:
            new_contents = contents.replace(str(curver), str(nextver))
            if contents == new_contents:
                raise TreeScriptError("File was not changed!")
            changes[file_] = new_contents
            diff += unified_diff(file_contents[file_].splitlines(), new_contents.splitlines(), fromfile=file_, tofile=file_, lineterm="")

    return changes, "\n".join(diff)
