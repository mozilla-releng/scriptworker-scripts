import json
import logging
import os.path
import pprint
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Self

from gql.transport.exceptions import TransportError

from landoscript.errors import LandoscriptError
from landoscript.lando import LandoAction, create_commit_action
from landoscript.util.diffs import diff_contents
from landoscript.util.log import log_file_contents
from scriptworker_client.github import extract_github_repo_owner_and_name
from scriptworker_client.github_client import GithubClient

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlatformConfig:
    platforms: list[str]
    path: str


@dataclass(frozen=True)
class IgnoreConfig:
    ignore_rules: dict[str, list[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class L10nBumpInfo:
    path: str
    name: str
    l10n_repo_url: str
    l10n_repo_target_branch: str
    platform_configs: list[PlatformConfig]
    ignore_config: IgnoreConfig = field(default_factory=IgnoreConfig)

    @classmethod
    def from_payload_data(cls, payload_data) -> Self:
        # copy to avoid modifying the original
        kwargs = deepcopy(payload_data)
        kwargs["platform_configs"] = [PlatformConfig(**pc) for pc in payload_data["platform_configs"]]
        kwargs["ignore_config"] = IgnoreConfig(payload_data.get("ignore_config", {}))
        return cls(**kwargs)


async def run(
    github_client: GithubClient,
    github_config: dict[str, str],
    public_artifact_dir: str,
    branch: str,
    l10n_bump_infos: list[L10nBumpInfo],
    dontbuild: bool,
    ignore_closed_tree: bool,
) -> list[LandoAction]:
    log.info("preparing to bump l10n changesets.")

    lando_actions = []
    for bump_config in l10n_bump_infos:
        log.info(f"considering {bump_config.name}")
        l10n_repo_url = bump_config.l10n_repo_url
        l10n_repo_target_branch = bump_config.l10n_repo_target_branch

        l10n_owner, l10n_repo = extract_github_repo_owner_and_name(l10n_repo_url)

        async with GithubClient(github_config, l10n_owner, l10n_repo) as l10n_github_client:
            # fetch initial files from github
            platform_config_files = [pc.path for pc in bump_config.platform_configs]
            files = [bump_config.path, *platform_config_files]
            try:
                log.info(f"fetching bump files from github: {files}")
                orig_files = await github_client.get_files(files, branch)
            except TransportError as e:
                raise LandoscriptError("couldn't retrieve bump files from github") from e

            log.debug("fetched file contents are:")
            for fn, contents in orig_files.items():
                log.debug(f"{fn}:")
                log.debug(contents)

            if orig_files[bump_config.path] is None:
                raise LandoscriptError(f"{bump_config.path} does not exist, cannot perform bump!")

            old_contents = json.loads(str(orig_files[bump_config.path]))
            orig_platform_files = {k: v for k, v in orig_files.items() if k in platform_config_files}

            # get new revision
            log.info("fetching new l10n revision")
            new_revision = await l10n_github_client.get_branch_head_oid(l10n_repo_target_branch)
            log.info(f"new l10n revision is {new_revision}")

            # build new versions of files
            new_contents = build_revision_dict(bump_config.ignore_config, bump_config.platform_configs, orig_platform_files, new_revision)
            log.debug(f"new contents of of {bump_config.path} are:")
            log.debug(new_contents)

            if old_contents == new_contents:
                log.warning(f"old and new contents of {bump_config.path} are the same, skipping bump...")
                continue

            # make diff
            diff = diff_contents(
                json.dumps(old_contents, sort_keys=True, indent=4, separators=(",", ": ")),
                json.dumps(new_contents, sort_keys=True, indent=4, separators=(",", ": ")),
                bump_config.path,
            )

            with open(os.path.join(public_artifact_dir, f"l10n-bump-{bump_config.name}.diff"), "w+") as f:
                f.write(diff)

            log.info(f"adding l10n bump commit for {bump_config.name}! diff contents omitted from log for brevity")
            log_file_contents(diff)

            # create commit message
            locale_map = build_locale_map(old_contents, new_contents)
            commitmsg = build_commit_message(bump_config.name, locale_map, dontbuild, ignore_closed_tree)

            # create action
            lando_actions.append(create_commit_action(commitmsg, diff))

    return lando_actions


def build_platform_dict(ignore_config: IgnoreConfig, platform_configs: list[PlatformConfig], orig_platform_files):
    """Build a dictionary of locale to list of platforms.

    Args:
        ignore_config (dict): key/value pairs (str/[str]) of locales and
            platforms that they _shouldn't_ be present for.
        platform_configs ([dict]): dictionaries consisting of a path to a
            shipped-locales style file (str) containing a list of locales
            applicable to the platforms ([str]) provided.
            and platforms ([str])
        orig_platform_files (dict): key/value pairs (str/str) of filenames
            and file contents. one entry must be provided for each path
            provided in `platform_configs`.

    Returns:
        dict: the platform dict

    """
    platform_dict = {}
    for platform_config in platform_configs:
        orig_contents = orig_platform_files[platform_config.path]
        for locale in orig_contents.splitlines():
            if locale in ("en-US",):
                continue
            existing_platforms = set(platform_dict.get(locale, {}).get("platforms", []))
            platforms = set(platform_config.platforms)
            ignore_platforms = set(ignore_config.ignore_rules.get(locale, []))
            platforms = (platforms | existing_platforms) - ignore_platforms
            platform_dict[locale] = {"platforms": sorted(list(platforms))}
    log.info("Built platform_dict:\n%s" % pprint.pformat(platform_dict))
    return platform_dict


# build_revision_dict_github {{{1
def build_revision_dict(ignore_config: IgnoreConfig, platform_configs: list[PlatformConfig], orig_platform_files, revision) -> dict:
    """Add l10n revision information to the ``platform_dict``. All locales will
    be bumped to head revision of the branch given in `l10n_repo_target_branch`
    in the repository that `client` is configured with.

    Args:
        ignore_config (dict): key/value pairs (str/[str]) of locales and
            platforms that they _shouldn't_ be present for.
        platform_configs ([dict]): dictionaries consisting of a path to a
            shipped-locales style file (str) containing a list of locales
            applicable to the platforms ([str]) provided.
            and platforms ([str])
        bump_config (dict): one of the dictionaries from the payload ``l10n_bump_info``.
            This dictionary must contain a `l10n_repo_target_branch`.
        revision (str): the revision to use for each locale entry

    Returns:
        dict: locale to dictionary of platforms and revision
    """
    log.info("Building revision dict...")
    platform_dict = build_platform_dict(ignore_config, platform_configs, orig_platform_files)

    for locale in platform_dict:
        # no longer supported; this item will be removed in the future
        platform_dict[locale]["pin"] = False
        platform_dict[locale]["revision"] = revision

    log.info("revision_dict:\n%s" % pprint.pformat(platform_dict))
    return platform_dict


# build_commit_message {{{1
def build_commit_message(name, locale_map, dontbuild=False, ignore_closed_tree=False):
    """Build a commit message for the bumper.

    Args:
        name (str): the human readable name for the path (e.g. Firefox l10n
            changesets)
        locale_map (dict): l10n changeset changes, keyed by locale
        dontbuild (bool, optional): whether to add ``DONTBUILD`` to the
            comment. Defaults to ``False``
        ignore_closed_tree (bool, optional): whether to add ``CLOSED TREE``
            to the comment. Defaults to ``False``.

    Returns:
        str: the commit message

    """
    comments = ""
    approval_str = "r=release a=l10n-bump"
    for locale, revision in sorted(locale_map.items()):
        comments += "%s -> %s\n" % (locale, revision)
    if dontbuild:
        approval_str += " DONTBUILD"
    if ignore_closed_tree:
        approval_str += " CLOSED TREE"
    message = "No Bug - Bumping %s %s\n\n" % (name, approval_str)
    message += comments
    return message


# build_locale_map {{{1
def build_locale_map(old_contents, new_contents):
    """Build a map of changed locales for the commit message.

    Args:
        old_contents (dict): the old l10n changesets
        new_contents (dict): the bumped l10n changesets

    Returns:
        dict: the changes per locale

    """
    locale_map = {}
    for key in old_contents:
        if key not in new_contents:
            locale_map[key] = "removed"
    for k, v in new_contents.items():
        if old_contents.get(k, {}).get("revision") != v["revision"]:
            locale_map[k] = v["revision"]
        if old_contents.get(k, {}).get("platforms") != v["platforms"]:
            locale_map[k] = v["platforms"]
    return locale_map
