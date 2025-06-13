import logging
import os.path
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import tomllib

from landoscript.errors import LandoscriptError
from landoscript.lando import LandoAction, create_commit_action
from landoscript.util.diffs import diff_contents
from landoscript.util.l10n import L10nFile, getL10nFilesFromToml
from scriptworker_client.github import extract_github_repo_owner_and_name
from scriptworker_client.github_client import GithubClient

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class TomlInfo:
    toml_path: str
    dest_path: str


@dataclass
class AndroidL10nImportInfo:
    from_repo_url: str
    toml_info: list[TomlInfo]

    @classmethod
    def from_payload_data(cls, payload_data) -> Self:
        # copy to avoid modifying the original
        kwargs = deepcopy(payload_data)
        kwargs["toml_info"] = [TomlInfo(**ti) for ti in payload_data["toml_info"]]
        return cls(**kwargs)


async def run(
    github_client: GithubClient, github_config: dict[str, str], public_artifact_dir: str, android_l10n_import_info: AndroidL10nImportInfo, to_branch: str
) -> list[LandoAction]:
    log.info("Preparing to import android l10n changesets.")

    l10n_repo_url = android_l10n_import_info.from_repo_url
    l10n_owner, l10n_repo = extract_github_repo_owner_and_name(l10n_repo_url)

    async with GithubClient(github_config, l10n_owner, l10n_repo) as l10n_github_client:
        toml_files = [info.toml_path for info in android_l10n_import_info.toml_info]
        # we always take the tip of the default branch when importing new strings
        toml_contents = await l10n_github_client.get_files(toml_files)
        l10n_files: list[L10nFile] = []

        missing = [fn for fn, contents in toml_contents.items() if contents is None]
        if missing:
            raise LandoscriptError(f"toml_file(s) {' '.join(missing)} are not present in repository")

        for info in android_l10n_import_info.toml_info:
            toml_file = info.toml_path
            log.info(f"processing toml file: {toml_file}")

            contents = tomllib.loads(str(toml_contents[toml_file]))
            src_file_prefix = Path(toml_file).parent
            dst_file_prefix = Path(info.dest_path)
            if "**" in contents["paths"][0]["reference"]:
                # localized file paths contain globs; we need that directory
                # structure to determine the files we need to fetch
                force_paths = await l10n_github_client.get_file_listing(str(src_file_prefix), depth_per_query=4)
            else:
                force_paths = []

            for src_name in getL10nFilesFromToml(toml_file, contents, force_paths):
                dst_name = dst_file_prefix / src_name.relative_to(src_file_prefix)
                l10n_files.append(L10nFile(src_name=str(src_name), dst_name=str(dst_name)))

        # fetch l10n_files from android-l10n
        src_files = [f.src_name for f in l10n_files]
        log.info(f"fetching updated files from l10n repository: {src_files}")
        new_files = await l10n_github_client.get_files(src_files)
        # we also need to update the toml files with locale metadata. we've
        # already fetched them above; so just add their contents by hand
        new_files.update(toml_contents)

        # fetch l10n_files from gecko repo
        # `l10n_files` will give us all of the files with translations in them
        dst_files = [f.dst_name for f in l10n_files]
        # we also need the gecko locations of the toml files
        for toml_info in android_l10n_import_info.toml_info:
            dst_files.append(f"{toml_info.dest_path}/l10n.toml")

        log.info(f"fetching original files from l10n repository: {dst_files}")
        orig_files = await github_client.get_files(dst_files, branch=to_branch)

        diffs = []
        for l10n_file in l10n_files:
            if l10n_file.dst_name not in orig_files:
                log.warning(f"WEIRD: {l10n_file.dst_name} not in orig_files, continuing anyways...")
                continue

            if l10n_file.src_name not in new_files:
                log.warning(f"WEIRD: {l10n_file.src_name} not in new_files, continuing anyways...")
                continue

            orig_file = orig_files[l10n_file.dst_name]
            new_file = new_files[l10n_file.src_name]
            if orig_file == new_file:
                log.warning(f"old and new contents of {l10n_file.dst_name} are the same, skipping bump...")
                continue

            diffs.append(diff_contents(orig_file, new_file, l10n_file.dst_name))

        for toml_info in android_l10n_import_info.toml_info:
            src_path = toml_info.toml_path
            dst_path = f"{toml_info.dest_path}/l10n.toml"

            if src_path not in new_files or dst_path not in orig_files:
                raise LandoscriptError(f"{src_path} is not available in the src and dest, cannot continue")

            orig_file = orig_files[dst_path]
            new_file = new_files[src_path]

            if orig_file == new_file:
                log.warning(f"old and new contents of {dst_path} are the same, skipping bump...")
                continue

            diffs.append(diff_contents(orig_file, new_file, dst_path))

        if not diffs:
            return []

        diff = "\n".join(diffs)

        with open(os.path.join(public_artifact_dir, "android-import.diff"), "w+") as f:
            f.write(diff)

        log.info("adding android l10n import diff! contents omitted from log for brevity")

        # We always ignore closed trees for android l10n imports.
        commitmsg = f"No Bug - Import translations from {l10n_repo_url} CLOSED TREE"
        return [create_commit_action(commitmsg, diff)]
