#!/usr/bin/env python
"""Treescript version manipulation."""

import logging
import os

import attr
from mozilla_version.gecko import FirefoxVersion, GeckoVersion, ThunderbirdVersion
from mozilla_version.mobile import MobileVersion

from treescript.exceptions import TaskVerificationError, TreeScriptError
from treescript.gecko import mercurial as vcs
from treescript.util.task import DONTBUILD_MSG, get_dontbuild, get_metadata_source_repo, get_version_bump_info

log = logging.getLogger(__name__)


ALLOWED_BUMP_FILES = (
    "browser/config/version.txt",
    "browser/config/version_display.txt",
    "config/milestone.txt",
    "mobile/android/version.txt",
    "mail/config/version.txt",
    "mail/config/version_display.txt",
)

_VERSION_CLASS_PER_BEGINNING_OF_PATH = {
    "browser/": FirefoxVersion,
    "config/milestone.txt": GeckoVersion,
    "mobile/android/": MobileVersion,
    "mail/": ThunderbirdVersion,
}

_VERSION_CLASS_PER_END_OF_SOURCE_REPO = {}


def _find_what_version_parser_to_use(file_, source_repo):
    version_classes = [cls for path, cls in _VERSION_CLASS_PER_BEGINNING_OF_PATH.items() if file_.startswith(path)]

    number_of_version_classes = len(version_classes)
    if number_of_version_classes > 1:
        raise TreeScriptError(f'File "{file_}" matched too many classes: {version_classes}')
    if number_of_version_classes > 0:
        return version_classes[0]

    log.info("Could not determine version class based on file path. Falling back to source_repo")

    version_classes = [cls for repo_name, cls in _VERSION_CLASS_PER_END_OF_SOURCE_REPO.items() if source_repo.endswith(repo_name)]
    try:
        return version_classes[0]
    except IndexError as exc:
        raise TreeScriptError(exc) from exc


def get_version(file_, parent_directory, source_repo):
    """Parse the version from file.

    Args:
        file_ (str): the version file path
        parent_directory (str): the directory file_ lives under

    Returns:
        str: the version.

    """
    abs_path = os.path.join(parent_directory, file_)
    log.info("Reading {} for version information.".format(abs_path))
    VersionClass = _find_what_version_parser_to_use(file_, source_repo)
    with open(abs_path, "r") as f:
        contents = f.read()
    log.info("Contents:")
    for line in contents.splitlines():
        log.info(" {}".format(line))
    lines = [line for line in contents.splitlines() if line and not line.startswith("#")]
    return VersionClass.parse(lines[-1])


async def bump_version(config, task, repo_path):
    """Perform a version bump.

    This function takes its inputs from task by using the ``get_version_bump_info``
    function from treescript.task. Using `next_version` and `files`, then
    calls do_version_bump to perform the work.1786807

    Args:
        config (dict): the running config
        task (dict): the running task
        repo_path (str): the source directory

    Returns:
        int: the number of commits created.

    """
    bump_info = get_version_bump_info(task)
    num_commits = 0

    source_repo = get_metadata_source_repo(task)
    changed = await do_bump_version(repo_path, bump_info["files"], bump_info["next_version"], source_repo)
    if changed:
        commit_msg = "Automatic version bump CLOSED TREE NO BUG a=release"
        if get_dontbuild(task):
            commit_msg += DONTBUILD_MSG
        await vcs.commit(config, repo_path, commit_msg)
        num_commits += 1
    return num_commits


async def do_bump_version(repo_path, files, next_version, source_repo):
    """Perform a version bump.

    This function takes its inputs from task by using the ``get_version_bump_info``
    function from treescript.task. Using `next_version` and `files`.

    This function does nothing (but logs) if the current version and next version
    match, and nothing if the next_version is actually less than current_version.

    Args:
        repo_path (str): the source directory
        files (List[str]): the files to bump
        next_version (str): the version to bump to
        source_repo (str): the source repository

    Raises:
        TaskverificationError: if a file specified is not allowed, or
                               if the file is not in the target repository.

    Returns:
        int: the number of commits created.

    """
    changed = False
    saved_next_version = next_version

    for file_ in files:
        abs_file = os.path.join(repo_path, file_)
        if file_ not in ALLOWED_BUMP_FILES:
            raise TaskVerificationError("{} is not in version bump whitelist".format(file_))
        if not os.path.exists(abs_file):
            raise TaskVerificationError("{} is not in repo".format(abs_file))

        VersionClass = _find_what_version_parser_to_use(file_, source_repo)
        curr_version = get_version(file_, repo_path, source_repo)
        next_version = VersionClass.parse(saved_next_version)

        try:
            curr_is_esr = curr_version.is_esr
            next_is_esr = next_version.is_esr
        except AttributeError:  # Fenix does not expose the is_esr attribute
            curr_is_esr = next_is_esr = False

        # XXX In the case of ESR, some files (like version.txt) show version numbers without `esr`
        # at the end.
        # For release-version-bump, next_version is provided with `esr` by Shipit, wuth
        # a list of files to bump. The esr suffix needs to be dropped from files
        # that do not have it.
        # For merge automation, `create_new_version` will keep the original suffix
        # by default, or change it if new_suffix is set for the file. There should
        # not be any cases where a suffix needs to be added or removed since create_new_version
        # handled it already.
        # That's why we do this late minute replacement and why we reset `next_version` at every
        # cycle of the loop
        if next_is_esr and not curr_is_esr:
            next_version = attr.evolve(next_version, is_esr=False)

        if next_version < curr_version:
            log.warning("Version bumping skipped due to conflicting values: (next version {} is < current version {})".format(next_version, curr_version))
            continue
        elif next_version == curr_version:
            log.info("Version bumping skipped due to unchanged values")
            continue
        else:
            changed = True
            replace_ver_in_file(abs_file, curr_version, next_version)

    return changed


def replace_ver_in_file(file_, curr_version, new_version):
    """Read in contents of `file` and then update version.

    Implementation detail: replaces instances of `curr_version` with `new_version`
    using python3 str.replace().

    Args:
        file_ (str): the path to the file
        curr_version (str): the current version
        new_version (str): the version to bump to

    Raises:
        Exception: if contents before and after match.

    """
    with open(file_, "r") as f:
        contents = f.read()
    new_contents = contents.replace(str(curr_version), str(new_version))
    if contents == new_contents:
        raise Exception("Did not expect no changes")
    with open(file_, "w") as f:
        f.write(new_contents)
