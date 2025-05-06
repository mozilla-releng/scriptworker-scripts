import logging
import os.path
import re
import string
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date
from typing import Self

import attr
from aiohttp import ClientSession
from mozilla_version.gecko import GeckoVersion
from mozilla_version.version import BaseVersion
from scriptworker.client import TaskVerificationError

from landoscript.actions import tag, version_bump
from landoscript.errors import LandoscriptError
from landoscript.lando import LandoAction, create_commit_action
from landoscript.util.diffs import diff_contents
from landoscript.util.log import log_file_contents
from landoscript.util.version import find_what_version_parser_to_use
from scriptworker_client.github_client import GithubClient, defaultdict

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class VersionFile:
    filename: str
    new_suffix: str = ""
    version_bump: str = ""


@dataclass(frozen=True)
class MergeInfo:
    to_branch: str
    fetch_version_from: str
    from_branch: str = ""
    base_tag: str = ""
    end_tag: str = ""
    merge_old_head: bool = False
    version_files: list[VersionFile] = field(default_factory=list)
    replacements: list[list[str]] = field(default_factory=list)
    regex_replacements: list[list[str]] = field(default_factory=list)

    @classmethod
    def from_payload_data(cls, payload_data) -> Self:
        # copy to avoid modifying the original
        kwargs = deepcopy(payload_data)
        kwargs["version_files"] = [VersionFile(**v) for v in payload_data.get("version_files", [])]
        return cls(**kwargs)


async def run(session: ClientSession, github_client: GithubClient, public_artifact_dir: str, merge_info: MergeInfo) -> list[LandoAction]:
    to_branch = merge_info.to_branch
    from_branch = merge_info.from_branch
    end_tag = merge_info.end_tag
    base_tag = merge_info.base_tag
    merge_old_head = merge_info.merge_old_head
    version_file = merge_info.fetch_version_from
    actions = []

    log.info("Starting merge day operations!")
    to_version = await get_version(github_client, version_file, to_branch)
    log.info(f"to_version is: {to_version}")
    if end_tag:
        end_revision = await github_client.get_branch_head_oid(to_branch)
        # End tag specifically uses the `to_version` _before_ we bump it
        # (because we're declaring its current version as "done")
        end_tag_fmted = end_tag.format(major_version=to_version.major_number)
        log.info(f"Adding end_tag: {end_tag_fmted}")
        actions.extend(await tag.run(session, tag.GitTagInfo(revision=end_revision, tags=[end_tag_fmted])))

    # We need to determine `bump_version`, which is what we will use when
    # performing version bumps later on. This version must be whatever version
    # is present on the `to_branch` immediately prior to the version bumps taking
    # place. When `from_branch` is present, this code will end up on `to_branch`
    # at that point. If there's no `from_branch`, whatever is currently on `to_branch`
    # is correct.
    if from_branch:
        bump_version = await get_version(github_client, version_file, from_branch)
        bump_branch = from_branch
        log.info(f"from_branch is present, got bump_version from it: {bump_version}")
        end_revision = await github_client.get_branch_head_oid(from_branch)

        # base tagging _only_ happens when we have a `from_branch` -- these are
        # scenarios where we're uplifting one branch to another, and beginning a new
        # version number on the `to_branch`, which we declare with the `BASE` tag.
        if base_tag:
            base_tag_fmted = base_tag.format(major_version=bump_version.major_number)
            log.info(f"Adding base_tag: {base_tag_fmted}")
            actions.extend(await tag.run(session, tag.GitTagInfo(revision=end_revision, tags=[base_tag_fmted])))
        if merge_old_head:
            log.info(f"Merging old head. target is from_branch ({from_branch}), strategy is theirs")
            # perform merge
            # `theirs` strategy means that the repo being modified will have its tree updated to match that
            # of the `target`.
            merge_msg = f"Update {to_branch} to {from_branch}"
            actions.append({"action": "merge-onto", "target": end_revision, "strategy": "theirs", "commit_message": merge_msg})
    else:
        if merge_old_head:
            raise TaskVerificationError("'from_branch' is required when merge_old_head is True or version_files are present")

        bump_version = to_version
        bump_branch = to_branch
        log.info(f"from_branch is not present, using to_version as bump_version: {bump_version}")

    if merge_info.version_files:
        log.info("Performing version bumps")
        files_by_new_suffix = defaultdict(list)
        bump_types = set()
        for vf in merge_info.version_files:
            if bump_type := vf.version_bump:
                bump_types.add(bump_type)
            files_by_new_suffix[vf.new_suffix].append(vf.filename)

        if len(bump_types) == 0:
            bump_types.add("")
        elif len(bump_types) != 1:
            raise TaskVerificationError(f"must provide zero or one `version_bump` type, got: {len(bump_types)}")

        bump_type = bump_types.pop()
        version_bump_infos = []
        for new_suffix, files in files_by_new_suffix.items():
            # Note that `bump_type` may be an empty string, which means a bump will
            # _not_ happen. ie: we may end up with a new suffix but the same version
            # number.
            next_version = get_new_version(bump_version, new_suffix, bump_type)
            version_bump_infos.append(version_bump.VersionBumpInfo(files=files, next_version=next_version))

        log.info(f"version_bump_infos is: {version_bump_infos}")
        actions.append(
            await version_bump.run(
                github_client,
                public_artifact_dir,
                bump_branch,
                version_bump_infos,
                dontbuild=False,
                munge_next_version=False,
            )
        )

    # process replacements, regex-replacements, and update clobber file
    replacements = merge_info.replacements
    regex_replacements = merge_info.regex_replacements
    diff = ""
    if replacements or regex_replacements:
        log.info("Performing replacements and regex_replacements")
        needed_files = []
        for r in replacements:
            needed_files.append(r[0])
        for r in regex_replacements:
            needed_files.append(r[0])

        orig_contents = await github_client.get_files(needed_files, bump_branch)
        # At the moment, there are no known cases of needing to replace with
        # a suffix...so we simply don't handle that here!
        new_contents = process_replacements(bump_version, replacements, regex_replacements, orig_contents)
        for fn in orig_contents:
            if orig_contents[fn] is None:
                raise LandoscriptError(f"Couldn't find file '{fn}' in repository!")

            diff += diff_contents(str(orig_contents[fn]), new_contents[fn], fn)

    log.info("Touching clobber file")
    orig_clobber_file = (await github_client.get_files("CLOBBER", bump_branch))["CLOBBER"]
    if orig_clobber_file is None:
        raise LandoscriptError("Couldn't find CLOBBER file in repository!")

    new_clobber_file = get_new_clobber_file(orig_clobber_file)
    diff += diff_contents(orig_clobber_file, new_clobber_file, "CLOBBER")

    log.info("replacements and clobber diff is:")
    log_file_contents(diff)

    with open(os.path.join(public_artifact_dir, "replacements.diff"), "w+") as f:
        f.write(diff)

    commitmsg = "No Bug - Update configs after merge day operations"
    actions.append(create_commit_action(commitmsg, diff))

    return actions


async def get_version(github_client: GithubClient, version_file: str, branch: str):
    resp = await github_client.get_files(version_file, branch)
    contents = resp[version_file]
    if contents is None:
        raise LandoscriptError(f"Couldn't find {version_file} in repository!")

    VersionClass = find_what_version_parser_to_use(version_file)
    lines = [line for line in contents.splitlines() if line and not line.startswith("#")]
    return VersionClass.parse(lines[-1])


def _get_attr_evolve_kwargs(version):
    kwargs = {
        "beta_number": None,
        "is_nightly": False,
    }
    if isinstance(version, GeckoVersion):
        kwargs["is_esr"] = False
    return kwargs


def get_new_version(version: BaseVersion, new_suffix="", bump_type=""):
    """Create a new version string. If `bump_type` is `major` the first part of
    the version will be increased by 1. If `bump_type` is `minor` the second part
    of the version will be increased by 1. Suffixes will be stripped from the
    result and `new_suffix` will be applied to it."""

    if bump_type == "major":
        new_version = version.bump("major_number")
    elif bump_type == "minor":
        new_version = version.bump("minor_number")
    else:
        # no bump; usually this means there's a new suffix
        new_version = version

    new_version = attr.evolve(new_version, **_get_attr_evolve_kwargs(new_version))
    new_version = f"{new_version}{new_suffix}"
    return new_version


class BashFormatter(string.Formatter):
    """BashFormatter: Safer bash strings.

    Ignore things that are probably bash variables when formatting.

    For example, this will be passed back unchanged:
    "MOZ_REQUIRE_SIGNING=${MOZ_REQUIRE_SIGNING-0}"
    while still allowing us to have:
    "Tagging {current_major_version}"
    """

    def get_value(self, key, args, kwargs):
        """If a value is not found, return the key."""
        if isinstance(key, str):
            return kwargs.get(key, "{" + key + "}")
        else:
            return string.Formatter().get_value(key, args, kwargs)


def replace(file_name, text, from_, to_, use_regex=False):
    """Replace text in a file."""
    log.info("Replacing %s -> %s in %s", from_, to_, file_name)

    if use_regex:
        new_text = re.sub(from_, to_, text)
    else:
        new_text = text.replace(from_, to_)

    if text == new_text:
        raise ValueError(f"{file_name} does not contain {from_}")

    return new_text


def process_replacements(version, replacements, regex_replacements, orig_contents):
    """Apply changes to repo required for merge/rebranding."""
    log.info("Processing replacements and regex-replacements")

    # Used in file replacements, further down.
    format_options = {
        "current_major_version": version.major_number,
        "next_major_version": version.major_number + 1,
        "current_weave_version": version.major_number + 2,
        "next_weave_version": version.major_number + 3,  # current_weave_version + 1
    }

    # Cope with bash variables in strings that we don't want to
    # be formatted in Python. We do this by ignoring {vars} we
    # aren't given keys for.
    fmt = BashFormatter()
    new_contents = {}
    for f, from_, to in replacements:
        from_ = fmt.format(from_, **format_options)
        to = fmt.format(to, **format_options)
        new_contents[f] = replace(f, orig_contents[f], from_, to)

    for f, from_, to in regex_replacements:
        from_ = from_.format(**format_options)
        to = fmt.format(to, **format_options)
        new_contents[f] = replace(f, orig_contents[f], from_, to, use_regex=True)

    return new_contents


def get_new_clobber_file(contents):
    """Update the clobber file in the root of the repo."""
    log.info("Updating clobber file")
    new_contents = ""
    for line in contents.splitlines():
        line = line.strip()
        if line.startswith("#") or line == "":
            new_contents += f"{line}\n"
    return f"{new_contents}Merge day clobber {str(date.today())}"
