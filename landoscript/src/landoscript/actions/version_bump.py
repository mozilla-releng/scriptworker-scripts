import logging
import typing
from difflib import unified_diff

import aiohttp
from mozilla_version.gecko import FirefoxVersion, GeckoVersion, ThunderbirdVersion
from mozilla_version.mobile import MobileVersion
from mozilla_version.version import BaseVersion
from scriptworker.exceptions import TaskVerificationError

from landoscript.github import GithubClient
from landoscript.types import Branch, Filename, LandoscriptConfig, SourceRepo, VersionBumpInfo

log = logging.getLogger(__name__)
FileContents = dict[str, str]

ALLOWED_BUMP_FILES = (
    "browser/config/version.txt",
    "browser/config/version_display.txt",
    "config/milestone.txt",
    "mobile/android/version.txt",
)

_VERSION_CLASS_PER_BEGINNING_OF_PATH = {
    "browser/": FirefoxVersion,
    "config/milestone.txt": GeckoVersion,
    "mobile/android/": MobileVersion,
    "mail/": ThunderbirdVersion,
}


async def run(
    config: LandoscriptConfig,
    github_client: GithubClient,
    session: aiohttp.ClientSession,
    source_repo: SourceRepo,
    branch: Branch,
    version_bump_info: VersionBumpInfo,
    dontbuild: bool = False,
    ignore_closed_tree: bool = False,
):
    lando_api = config["lando_api"]
    next_version = version_bump_info["next_version"]
    orig_files = await github_client.get_files(version_bump_info["files"], branch)
    diff = ""
    for file, orig in orig_files.items():
        if file not in ALLOWED_BUMP_FILES:
            raise TaskVerificationError("{} is not in version bump whitelist".format(file))

        cur, next_ = get_cur_and_next_version(file, orig, next_version)
        if next_ < cur:
            log.warning("Version bumping skipped due to conflicting values: (next version {} is < current version {})".format(next_, cur))
            continue
        elif next_ == cur:
            log.info("Version bumping skipped due to unchanged values")
            continue

        modified = orig.replace(str(cur), str(next_))
        if orig == modified:
            raise Exception("something should've changed!")

        diff += "\n".join(unified_diff(orig.splitlines(), modified.splitlines(), fromfile=file, tofile=file, lineterm=""))
        if orig.endswith("\n"):
            diff += "\n"

    if not diff:
        # or raise an exception?
        return

    header = """\
Author: Release Engineering Landoscript <release+landoscript@mozilla.com>

    Automatic version bump NO BUG a=release"""
    if ignore_closed_tree:
        header += " CLOSED TREE"
    if dontbuild:
        header += " DONTBUILD"
    header += "\n"

    # TODO: ideally there would be a lando endpoint for this, because `repo_name`
    # is ultimately an identifier in lando's config/database, but landoscript
    # tasks are identified by a particular repository
    repo_name = source_repo.split("/")[-1]

    _ = await session.post(
        f"{lando_api}/api/v1/{repo_name}/{branch}",
        json={
            "actions": [
                {
                    "action": "add-commit",
                    "content": header + diff,
                },
            ],
        },
    )


def _find_what_version_parser_to_use(file):
    version_classes = [cls for path, cls in _VERSION_CLASS_PER_BEGINNING_OF_PATH.items() if file.startswith(path)]

    number_of_version_classes = len(version_classes)
    if number_of_version_classes > 1:
        raise Exception(f'File "{file}" matched too many classes: {version_classes}')
    if number_of_version_classes > 0:
        return version_classes[0]

    raise Exception(f"Could not determine version class based on file path for {file}")


def get_cur_and_next_version(filename: Filename, orig_contents: str, next_version: str) -> tuple[BaseVersion, BaseVersion]:
    VersionClass: BaseVersion = _find_what_version_parser_to_use(filename)
    lines = [line for line in orig_contents.splitlines() if line and not line.startswith("#")]
    cur = VersionClass.parse(lines[-1])

    # Special case for ESRs; make sure the next version is consistent with the
    # current version with respect to whether or not it includes the `esr`
    # suffix.
    if next_version.endswith("esr") and not typing.cast(GeckoVersion, cur).is_esr:
        next_version = next_version.replace("esr", "")

    next_ = VersionClass.parse(next_version)

    return cur, next_
