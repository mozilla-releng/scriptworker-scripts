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
from scriptworker_client.github_client import GithubClient, defaultdict

from landoscript.actions import l10n_bump, tag, version_bump
from landoscript.errors import LandoscriptError
from landoscript.lando import LandoAction, create_commit_action
from landoscript.util.diffs import diff_contents
from landoscript.util.log import log_file_contents
from landoscript.util.version import find_what_version_parser_to_use

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
    # TODO: to_revision should be required after all callers are updated to use it
    to_revision: str = ""
    from_branch: str = ""
    from_revision: str = ""
    base_tag: str = ""
    end_tag: str = ""
    merge_old_head: bool = False
    update_clobber_file: bool = True
    l10n_bump_info: list[l10n_bump.L10nBumpInfo] = field(default_factory=list)
    version_files: list[VersionFile] = field(default_factory=list)
    replacements: list[list[str]] = field(default_factory=list)
    regex_replacements: list[list[str]] = field(default_factory=list)

    # TODO: add __post_init__ to require `from_revision` when `from_branch` is
    # present after all callers are already doing so

    @classmethod
    def from_payload_data(cls, payload_data) -> Self:
        # copy to avoid modifying the original
        kwargs = deepcopy(payload_data)
        kwargs["version_files"] = [VersionFile(**v) for v in payload_data.get("version_files", [])]
        kwargs["l10n_bump_info"] = [l10n_bump.L10nBumpInfo.from_payload_data(lbi) for lbi in payload_data.get("l10n_bump_info", [])]
        return cls(**kwargs)


async def run(
    session: ClientSession, github_client: GithubClient, github_config: dict[str, str], public_artifact_dir: str, merge_info: MergeInfo
) -> list[LandoAction]:
    to_branch = merge_info.to_branch
    from_branch = merge_info.from_branch
    to_revision = merge_info.to_revision
    from_revision = merge_info.from_revision
    end_tag = merge_info.end_tag
    base_tag = merge_info.base_tag
    merge_old_head = merge_info.merge_old_head
    update_clobber_file = merge_info.update_clobber_file
    version_file = merge_info.fetch_version_from
    actions = []

    log.info("Starting merge day operations!")
    if not to_revision:
        # TODO: remove this fallback once `to_revision` is required
        to_revision = await github_client.get_branch_head_oid(to_branch)

    to_version = await get_version(github_client, version_file, to_revision)

    log.info(f"to_version is: {to_version}")
    if end_tag:
        # `end_revision` is purposely made to be whatever the current tip of `to_branch`
        # is when a landoscript task runs (as opposed to, eg: using the `to_revision`).
        # This guards against a task being created, something being pushed to the
        # `to_branch`, and then the `END` tag ending up on an outdated revision.
        # Even in a case where multiple versions of the same task are scheduled
        # and race against one another the tag cannot end up in the wrong place so
        # long as the `version` in it was fetched from a concrete revision. (If a race
        # does take place, the second task will attempt to move a tag, which will
        # fail the task.)
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
        if from_revision:
            bump_version = await get_version(github_client, version_file, from_revision)
            # Unlike tagging the `to_branch`, tagging the `from_branch` must be done
            # against a concrete revision known at task scheduling time. This is because
            # that revision is used as the merge target, and the tag must go on that
            # specific revision.
            end_revision = from_revision
        else:
            # TODO: remove this fallback once `from_revision` is being passed whenever
            # `from_branch is
            bump_version = await get_version(github_client, version_file, from_branch)
            end_revision = await github_client.get_branch_head_oid(from_branch)

        bump_revision = end_revision
        log.info(f"from_branch is present, got bump_version from it: {bump_version}")

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
            merge_msg = f"Promote {from_branch} to {to_branch}"
            actions.append({"action": "merge-onto", "target": end_revision, "strategy": "theirs", "commit_message": merge_msg})
    else:
        if merge_old_head:
            raise TaskVerificationError("'from_branch' is required when merge_old_head is True or version_files are present")

        bump_version = to_version
        bump_revision = to_revision
        log.info(f"from_branch is not present, using to_version as bump_version: {bump_version}")

    if merge_info.l10n_bump_info:
        actions.extend(await l10n_bump.run(github_client, github_config, public_artifact_dir, bump_revision, merge_info.l10n_bump_info, False, True))

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
        actions.extend(
            await version_bump.run(
                github_client,
                public_artifact_dir,
                bump_revision,
                version_bump_infos,
                dontbuild=False,
                munge_next_version=False,
            )
        )

    # process replacements, regex-replacements, and update clobber file
    replacements = merge_info.replacements
    regex_replacements = merge_info.regex_replacements

    files_to_diff = []

    if replacements or regex_replacements:
        log.info("Performing replacements and regex_replacements")
        needed_files = []
        for r in replacements:
            needed_files.append(r[0])
        for r in regex_replacements:
            needed_files.append(r[0])

        orig_contents = await github_client.get_files(needed_files, bump_revision)
        # At the moment, there are no known cases of needing to replace with
        # a suffix...so we simply don't handle that here!
        new_contents = process_replacements(bump_version, replacements, regex_replacements, orig_contents)
        for fn in orig_contents:
            if orig_contents[fn] is None:
                raise LandoscriptError(f"Couldn't find file '{fn}' in repository!")
            files_to_diff.append((fn, str(orig_contents[fn]), new_contents[fn]))

    if update_clobber_file:
        log.info("Touching clobber file")
        orig_clobber_file = (await github_client.get_files("CLOBBER", bump_revision))["CLOBBER"]
        if orig_clobber_file is None:
            raise LandoscriptError("Couldn't find CLOBBER file in repository!")

        new_clobber_file = get_new_clobber_file(orig_clobber_file)
        files_to_diff.append(("CLOBBER", orig_clobber_file, new_clobber_file))

        files_to_diff.sort(key=lambda x: x[0])

    # Generate diffs in sorted order
    diffs = []
    for file_path, orig_file, new_file in files_to_diff:
        diffs.append(diff_contents(orig_file, new_file, file_path))

    diff = "\n".join(diffs)

    log.info("replacements and clobber diff is:")
    log_file_contents(diff)

    with open(os.path.join(public_artifact_dir, "replacements.diff"), "w+") as f:
        f.write(diff)

    commitmsg = "No Bug - Update configs after merge day operations a=release"
    # keep the uglier magic strings out of the first line
    # also put them on their own lines to make it clear that they are
    # distinct from one another
    commitmsg += "\n"
    commitmsg += "\nIGNORE BROKEN CHANGESETS"
    commitmsg += "\nCLOSED TREE"
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
