#!/usr/bin/env python
"""Treescript version manipulation."""

import logging
import os
from distutils.version import StrictVersion

from mozilla_version.fenix import FenixVersion
from mozilla_version.gecko import FennecVersion, FirefoxVersion, GeckoVersion, ThunderbirdVersion

from treescript.exceptions import TaskVerificationError, TreeScriptError
from treescript.task import DONTBUILD_MSG, get_dontbuild, get_vcs_module, get_version_bump_info

log = logging.getLogger(__name__)


ALLOWED_BUMP_FILES = (
    "browser/config/version.txt",
    "browser/config/version_display.txt",
    "config/milestone.txt",
    "mail/config/version.txt",
    "mail/config/version_display.txt",
    "suite/config/version.txt",
    "suite/config/version_display.txt",
    "version.txt",  # Fenix
)


class SuiteVersion(StrictVersion):
    @classmethod
    def parse(cls, version_string):
        s = cls()
        super(SuiteVersion, s).parse(version_string)
        return s

    def bump(self, field):
        if field == "minor_number":
            index = 1
            ver_parts = list(self.version)
            ver_parts[index] += 1

            self.version = tuple(ver_parts)


_VERSION_CLASS_PER_BEGINNING_OF_PATH = {
    "browser/": FirefoxVersion,
    "config/milestone.txt": GeckoVersion,
    "mobile/android/": FennecVersion,
    "mail/": ThunderbirdVersion,
    "suite/": SuiteVersion,
    "version.txt": FenixVersion,
}


def _find_what_version_parser_to_use(file_):
    start_string_then_version_class = [cls for path, cls in _VERSION_CLASS_PER_BEGINNING_OF_PATH.items() if file_.startswith(path)]

    try:
        return start_string_then_version_class[0]
    except IndexError as exc:
        raise TreeScriptError(exc) from exc


def get_version(file_, parent_directory=None):
    """Parse the version from file.

    Args:
        file_ (str): the version file path
        parent_directory (str): the directory file_ lives under

    Returns:
        str: the version.

    """
    abs_path = os.path.join(parent_directory, file_)
    log.info("Reading {} for version information.".format(abs_path))
    VersionClass = _find_what_version_parser_to_use(file_)
    with open(abs_path, "r") as f:
        contents = f.read()
    log.info("Contents:")
    for line in contents.splitlines():
        log.info(" {}".format(line))
    lines = [line for line in contents.splitlines() if line and not line.startswith("#")]
    return VersionClass.parse(lines[-1])


async def bump_version(config, task, repo_path, repo_type):
    """Perform a version bump.

    This function takes its inputs from task by using the ``get_version_bump_info``
    function from treescript.task. Using `next_version` and `files`, then
    calls do_version_bump to perform the work.

    Args:
        config (dict): the running config
        task (dict): the running task
        repo_path (str): the source directory

    Returns:
        int: the number of commits created.

    """
    bump_info = get_version_bump_info(task)
    num_commits = 0

    changed = await do_bump_version(config, repo_path, bump_info["files"], bump_info["next_version"])
    vcs = get_vcs_module(repo_type)
    if changed:
        commit_msg = "Automatic version bump CLOSED TREE NO BUG a=release"
        if get_dontbuild(task):
            commit_msg += DONTBUILD_MSG
        await vcs.commit(config, repo_path, commit_msg)
        num_commits += 1
    return num_commits


async def do_bump_version(config, repo_path, files, next_version):
    """Perform a version bump.

    This function takes its inputs from task by using the ``get_version_bump_info``
    function from treescript.task. Using `next_version` and `files`.

    This function does nothing (but logs) if the current version and next version
    match, and nothing if the next_version is actually less than current_version.

    Args:
        config (dict): the running config
        task (dict): the running task
        repo_path (str): the source directory

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

        VersionClass = _find_what_version_parser_to_use(file_)
        curr_version = get_version(file_, repo_path)
        next_version = VersionClass.parse(saved_next_version)

        try:
            is_esr = curr_version.is_esr
        except AttributeError:  # Fenix does not expose the is_esr attribute
            is_esr = False

        # XXX In the case of ESR, some files (like version.txt) show version numbers without `esr`
        # at the end. next_version is usually provided without `esr` too.
        # That's why we do this late minute replacement and why we reset `next_version` at every
        # cycle of the loop
        if is_esr and not any(
            (
                next_version.is_esr,  # No need to append esr again
                # We don't want XX.Ya1esr nor XX.YbNesr
                next_version.is_aurora_or_devedition,
                next_version.is_beta,
            )
        ):
            next_version = VersionClass.parse("{}esr".format(next_version))

        if next_version < curr_version:
            log.warning("Version bumping skipped due to conflicting values: " "(next version {} is < current version {})".format(next_version, curr_version))
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
