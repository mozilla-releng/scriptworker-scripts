import datetime
import logging
import os.path
import typing
from typing import TypedDict

from gql.transport.exceptions import TransportError
from mozilla_version.gecko import FirefoxVersion, GeckoVersion, ThunderbirdVersion
from mozilla_version.mobile import MobileVersion
from mozilla_version.version import BaseVersion
from scriptworker.exceptions import TaskVerificationError

from landoscript.errors import LandoscriptError
from landoscript.lando import LandoAction
from landoscript.util.diffs import diff_contents
from scriptworker_client.github_client import GithubClient

log = logging.getLogger(__name__)

# A list of files that this action is allowed to operate on.
ALLOWED_BUMP_FILES = (
    "browser/config/version.txt",
    "browser/config/version_display.txt",
    "config/milestone.txt",
    "mobile/android/version.txt",
    "mail/config/version.txt",
    "mail/config/version_display.txt",
)

# A mapping of bump file prefixes to parsers for their contents.
_VERSION_CLASS_PER_BEGINNING_OF_PATH = {
    "browser/": FirefoxVersion,
    "config/milestone.txt": GeckoVersion,
    "mobile/android/": MobileVersion,
    "mail/": ThunderbirdVersion,
}


def log_file_contents(contents):
    for line in contents.splitlines():
        log.info(line)


class VersionBumpInfo(TypedDict):
    next_version: str
    files: list[str]


async def run(
    github_client: GithubClient,
    public_artifact_dir: str,
    branch: str,
    version_bump_info: VersionBumpInfo,
    dontbuild: bool,
) -> LandoAction:
    """Perform version bumps on the files given in `version_bump_info`, if necessary."""

    next_version = version_bump_info["next_version"]

    for file in version_bump_info["files"]:
        if file not in ALLOWED_BUMP_FILES:
            raise TaskVerificationError("{} is not in version bump allowlist".format(file))

    try:
        log.info("fetching bump files from github")
        orig_files = await github_client.get_files(version_bump_info["files"], branch)
    except TransportError as e:
        raise LandoscriptError("couldn't retrieve bump files from github") from e

    log.info("got files")
    for file, contents in orig_files.items():
        log.info(f"{file} contents:")
        log_file_contents(contents)

    diff = ""
    for file, orig in orig_files.items():
        if not orig:
            raise LandoscriptError(f"{file} does not exist!")

        log.info(f"considering {file}")
        cur, next_ = get_cur_and_next_version(file, orig, next_version)
        if next_ < cur:
            log.warning(f"{file}: Version bumping skipped due to conflicting values: (next version {next_} is < current version {cur})")
            continue
        elif next_ == cur:
            log.info(f"{file}: Version bumping skipped due to unchanged values")
            continue

        modified = orig.replace(str(cur), str(next_))
        if orig == modified:
            raise LandoscriptError("file not modified, this should be impossible")

        log.info(f"{file}: successfully bumped! new contents are:")
        log_file_contents(modified)

        diff += diff_contents(orig, modified, file)

    if not diff:
        log.info("no files to bump")
        return {}

    with open(os.path.join(public_artifact_dir, "version-bump.diff"), "w+") as f:
        f.write(diff)

    log.info("adding version bump commit! diff contents are:")
    log_file_contents(diff)

    author = "Release Engineering Landoscript <release+landoscript@mozilla.com>"
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # version bumps always ignore a closed tree
    commitmsg = "Subject: Automatic version bump NO BUG a=release CLOSED TREE"
    if dontbuild:
        commitmsg += " DONTBUILD"

    return {"action": "create-commit", "commitmsg": commitmsg, "diff": diff, "date": timestamp, "author": author}


def find_what_version_parser_to_use(file):
    version_classes = [cls for path, cls in _VERSION_CLASS_PER_BEGINNING_OF_PATH.items() if file.startswith(path)]

    number_of_version_classes = len(version_classes)
    if number_of_version_classes > 1:
        raise LandoscriptError(f'File "{file}" matched too many classes: {version_classes}')
    if number_of_version_classes > 0:
        return version_classes[0]

    raise LandoscriptError(f"Could not determine version class based on file path for {file}")


def get_cur_and_next_version(filename, orig_contents, next_version):
    VersionClass: BaseVersion = find_what_version_parser_to_use(filename)
    lines = [line for line in orig_contents.splitlines() if line and not line.startswith("#")]
    cur = VersionClass.parse(lines[-1])

    # Special case for ESRs; make sure the next version is consistent with the
    # current version with respect to whether or not it includes the `esr`
    # suffix.
    if next_version.endswith("esr") and not typing.cast(GeckoVersion, cur).is_esr:
        next_version = next_version.replace("esr", "")

    next_ = VersionClass.parse(next_version)

    return cur, next_
