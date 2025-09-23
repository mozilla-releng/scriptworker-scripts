import logging
import os.path
import typing
from dataclasses import dataclass

from gql.transport.exceptions import TransportError
from mozilla_version.gecko import GeckoVersion
from mozilla_version.version import BaseVersion
from scriptworker.exceptions import TaskVerificationError
from scriptworker_client.github_client import GithubClient

from landoscript.errors import LandoscriptError
from landoscript.lando import LandoAction, create_commit_action
from landoscript.util.diffs import diff_contents
from landoscript.util.log import log_file_contents
from landoscript.util.version import find_what_version_parser_to_use

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


@dataclass(frozen=True)
class VersionBumpInfo:
    next_version: str
    files: list[str]


async def run(
    github_client: GithubClient,
    public_artifact_dir: str,
    branch: str,
    version_bump_infos: list[VersionBumpInfo],
    dontbuild: bool = True,
    munge_next_version: bool = True,
) -> list[LandoAction]:
    """Perform version bumps on the files given in each `version_bump_info`, if necessary.

    If `munge_next_version` is True, the calculated next_version may be adjusted
    based on the contents of each file being bumped. The only known use case for this at
    the time of writing is when running the `release-to-esr` merge automation. Future uses
    are discouraged, and should be avoided if at all possible."""

    diffs = []

    for version_bump_info in version_bump_infos:
        next_version = version_bump_info.next_version

        for file in version_bump_info.files:
            if file not in ALLOWED_BUMP_FILES:
                raise TaskVerificationError("{} is not in version bump allowlist".format(file))

        try:
            log.info("fetching bump files from github")
            orig_files = await github_client.get_files(version_bump_info.files, branch)
        except TransportError as e:
            raise LandoscriptError("couldn't retrieve bump files from github") from e

        log.info("got files")
        for file, contents in orig_files.items():
            log.info(f"{file} contents:")
            log_file_contents(str(contents))

        # Sort files by path to ensure consistent diff ordering
        sorted_files = sorted(orig_files.keys())
        for file in sorted_files:
            orig = orig_files[file]
            if not orig:
                raise LandoscriptError(f"{file} does not exist!")

            log.info(f"considering {file}")
            cur, next_ = get_cur_and_next_version(file, orig, next_version, munge_next_version)
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

            diffs.append(diff_contents(orig, modified, file))

    if not diffs:
        log.info("no files to bump")
        return []

    def extract_path(diff_text):
        return diff_text.split("\n", 1)[0].split(" ")[2][2:]

    diffs = sorted(diffs, key=extract_path)
    diff = "\n".join(diffs)

    with open(os.path.join(public_artifact_dir, "version-bump.diff"), "w+") as f:
        f.write(diff)

    log.info("adding version bump commit! diff contents are:")
    log_file_contents(diff)

    # version bumps always ignore a closed tree
    commitmsg = "Automatic version bump NO BUG a=release CLOSED TREE"
    if dontbuild:
        commitmsg += " DONTBUILD"

    return [create_commit_action(commitmsg, diff)]


def get_cur_and_next_version(filename, orig_contents, next_version, munge_next_version):
    VersionClass: BaseVersion = find_what_version_parser_to_use(filename)
    lines = [line for line in orig_contents.splitlines() if line and not line.startswith("#")]
    cur = VersionClass.parse(lines[-1])

    # Special case for ESRs; make sure the next version is consistent with the
    # current version with respect to whether or not it includes the `esr`
    # suffix.
    if munge_next_version and next_version.endswith("esr") and not typing.cast(GeckoVersion, cur).is_esr:
        next_version = next_version.replace("esr", "")

    next_ = VersionClass.parse(next_version)

    return cur, next_
