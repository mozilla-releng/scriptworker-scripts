#!/usr/bin/env python
"""Treescript version manipulation."""

import logging
import os

from mozilla_version.gecko import (
    FirefoxVersion,
    FennecVersion,
    GeckoVersion,
    ThunderbirdVersion,
)
from scriptworker.utils import get_single_item_from_sequence

from treescript.utils import DONTBUILD_MSG
from treescript.exceptions import TaskVerificationError
from treescript.mercurial import run_hg_command
from treescript.task import get_version_bump_info, get_dontbuild

log = logging.getLogger(__name__)


ALLOWED_BUMP_FILES = (
    'browser/config/version.txt',
    'browser/config/version_display.txt',
    'config/milestone.txt',
    'mail/config/version.txt',
    'mail/config/version_display.txt',
    'mobile/android/config/version-files/beta/version.txt',
    'mobile/android/config/version-files/beta/version_display.txt',
    'mobile/android/config/version-files/release/version.txt',
    'mobile/android/config/version-files/release/version_display.txt',
)


def _get_version(file):
    """Parse the version from file."""
    log.info("Reading {} for version information.".format(file))
    with open(file, 'r') as f:
        contents = f.read()
    log.info("Contents:")
    for line in contents.splitlines():
        log.info(" {}".format(line))
    lines = [l for l in contents.splitlines() if l and
             not l.startswith("#")]
    return lines[-1]


async def bump_version(context):
    """Perform a version bump.

    This function takes its inputs from context.task by using the ``get_version_bump_info``
    function from treescript.task. Using `next_version` and `files`.

    This function does nothing (but logs) if the current version and next version
    match, and nothing if the next_version is actually less than current_version.

    raises:
        TaskverificationError: if a file specified is not allowed, or
                               if the file is not in the target repository.

    """
    bump_info = get_version_bump_info(context.task)
    files = bump_info['files']
    changed = False

    for file in files:
        abs_file = os.path.join(context.repo, file)
        if file not in ALLOWED_BUMP_FILES:
            raise TaskVerificationError("Specified file to version bump is not in whitelist")
        if not os.path.exists(abs_file):
            raise TaskVerificationError("Specified file is not in repo")

        VersionClass = _find_what_version_parser_to_use(file)
        curr_version = VersionClass.parse(_get_version(abs_file))
        next_version = VersionClass.parse(bump_info['next_version'])

        # XXX In the case of ESR, some files (like version.txt) show version numbers without `esr`
        # at the end. next_version is usually provided without `esr` too.
        # That's why we do this late minute replacement and why we reset `next_version` at every
        # cycle of the loop
        if curr_version.is_esr and not any((
            next_version.is_esr,     # No need to append esr again
            # We don't want XX.Ya1esr nor XX.YbNesr
            next_version.is_aurora_or_devedition,
            next_version.is_beta,
        )):
            next_version = VersionClass.parse('{}esr'.format(bump_info['next_version']))

        if next_version < curr_version:
            log.warning("Version bumping skipped due to conflicting values: "
                        "(next version {} is < current version {})"
                        .format(next_version, curr_version)
                        )
            continue
        elif next_version == curr_version:
            log.info("Version bumping skipped due to unchanged values")
            continue
        else:
            changed = True
            replace_ver_in_file(abs_file, curr_version, next_version)

    if changed:
        dontbuild = get_dontbuild(context.task)
        commit_msg = 'Automatic version bump CLOSED TREE NO BUG a=release'
        if dontbuild:
            commit_msg += DONTBUILD_MSG
        await run_hg_command(context, 'commit', '-m', commit_msg,
                             local_repo=context.repo)


_VERSION_CLASS_PER_BEGINNING_OF_PATH = {
    'browser/': FirefoxVersion,
    'config/milestone.txt': GeckoVersion,
    'mobile/android/': FennecVersion,
    'mail/': ThunderbirdVersion,
}


def _find_what_version_parser_to_use(file):
    start_string_then_version_class = get_single_item_from_sequence(
        sequence=_VERSION_CLASS_PER_BEGINNING_OF_PATH.items(),
        condition=lambda beginning_of_path_then_version_class: file.startswith(
            beginning_of_path_then_version_class[0]
        ),
    )

    return start_string_then_version_class[1]


def replace_ver_in_file(file, curr_version, new_version):
    """Read in contents of `file` and then update version.

    Implementation detail: replaces instances of `curr_version` with `new_version`
    using python3 str.replace().

    raises:
        Exception: if contents before and after match.

    """
    with open(file, 'r') as f:
        contents = f.read()
    new_contents = contents.replace(str(curr_version), str(new_version))
    if contents == new_contents:
        raise Exception("Did not expect no changes")
    with open(file, 'w') as f:
        f.write(new_contents)
