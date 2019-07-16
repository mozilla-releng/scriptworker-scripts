#!/usr/bin/env python
"""Treescript version manipulation."""

from distutils.version import StrictVersion, LooseVersion
import logging
import os

from treescript.utils import DONTBUILD_MSG
from treescript.exceptions import TaskVerificationError
from treescript.mercurial import run_hg_command
from treescript.task import get_version_bump_info, get_dontbuild

log = logging.getLogger(__name__)


ALLOWED_BUMP_FILES = (
    "browser/config/version.txt",
    "browser/config/version_display.txt",
    "config/milestone.txt",
    "mail/config/version.txt",
    "mail/config/version_display.txt",
    "mobile/android/config/version-files/beta/version.txt",
    "mobile/android/config/version-files/beta/version_display.txt",
    "mobile/android/config/version-files/release/version.txt",
    "mobile/android/config/version-files/release/version_display.txt",
)


def _get_version(file):
    """Parse the version from file."""
    log.info("Reading {} for version information.".format(file))
    with open(file, "r") as f:
        contents = f.read()
    log.info("Contents:")
    for line in contents.splitlines():
        log.info(" {}".format(line))
    lines = [l for l in contents.splitlines() if l and not l.startswith("#")]
    return lines[-1]


async def bump_version(config, task, directory):
    """Perform a version bump.

    This function takes its inputs from task by using the ``get_version_bump_info``
    function from treescript.task. Using `next_version` and `files`.

    This function does nothing (but logs) if the current version and next version
    match, and nothing if the next_version is actually less than current_version.

    raises:
        TaskverificationError: if a file specified is not allowed, or
                               if the file is not in the target repository.

    """
    bump_info = get_version_bump_info(task)
    next_version = bump_info["next_version"]
    old_next_version = None
    files = bump_info["files"]
    changed = False
    for file_ in files:
        if old_next_version:
            next_version = old_next_version
        abs_file = os.path.join(directory, file_)
        if file_ not in ALLOWED_BUMP_FILES:
            raise TaskVerificationError(f"{file_} is not in version bump whitelist")
        if not os.path.exists(abs_file):
            raise TaskVerificationError(f"{abs_file} is not in repo")
        curr_version = _get_version(abs_file)

        Comparator = StrictVersion
        if curr_version.endswith("esr") or next_version.endswith("esr"):
            #  We use LooseVersion for ESR because StrictVersion can't parse the trailing
            # 'esr', but StrictVersion otherwise because it can sort X.0bN lower than X.0
            Comparator = LooseVersion
        if Comparator(next_version) < Comparator(curr_version):
            log.warning(
                "Version bumping skipped due to conflicting values: "
                "(next version {} is < current version {})".format(
                    next_version, curr_version
                )
            )
            continue
        elif Comparator(next_version) == Comparator(curr_version):
            log.info("Version bumping skipped due to unchanged values")
            continue
        else:
            changed = True
            if curr_version.endswith("esr"):
                # Only support esr addition if already an esr string.
                if not next_version.endswith("esr"):
                    old_next_version = next_version
                    next_version = next_version + "esr"
            replace_ver_in_file(
                file=abs_file, curr_version=curr_version, new_version=next_version
            )
    if changed:
        dontbuild = get_dontbuild(task)
        commit_msg = "Automatic version bump CLOSED TREE NO BUG a=release"
        if dontbuild:
            commit_msg += DONTBUILD_MSG
        await run_hg_command(config, "commit", "-m", commit_msg, local_repo=directory)


def replace_ver_in_file(file, curr_version, new_version):
    """Read in contents of `file` and then update version.

    Implementation detail: replaces instances of `curr_version` with `new_version`
    using python3 str.replace().

    raises:
        Exception: if contents before and after match.

    """
    with open(file, "r") as f:
        contents = f.read()
    new_contents = contents.replace(curr_version, new_version)
    if contents == new_contents:
        raise Exception("Did not expect no changes")
    with open(file, "w") as f:
        f.write(new_contents)
