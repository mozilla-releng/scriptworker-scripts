import logging
import os.path
from pathlib import Path
from typing import TypedDict

import tomli

from landoscript.errors import LandoscriptError
from landoscript.lando import LandoAction, create_commit_action
from landoscript.util.diffs import diff_contents
from landoscript.util.l10n import L10nFile, getL10nFilesFromToml
from landoscript.util.log import log_file_contents
from scriptworker_client.github_client import GithubClient

log = logging.getLogger(__name__)


class TomlInfo(TypedDict):
    toml_path: str


class AndroidL10nSyncInfo(TypedDict):
    from_repo_url: str
    from_branch: str
    toml_info: list[TomlInfo]


async def run(github_client: GithubClient, public_artifact_dir: str, android_l10n_sync_info: AndroidL10nSyncInfo, to_branch: str) -> LandoAction:
    log.info("Preparing to sync android l10n changesets.")
    from_branch = android_l10n_sync_info["from_branch"]

    toml_files = [info["toml_path"] for info in android_l10n_sync_info["toml_info"]]
    toml_contents = await github_client.get_files(toml_files, branch=from_branch)
    l10n_files: list[L10nFile] = []

    for info in android_l10n_sync_info["toml_info"]:
        toml_file = info["toml_path"]
        log.info(f"processing toml file: {toml_file}")

        if toml_contents[toml_file] is None:
            raise LandoscriptError(f"toml_file '{toml_file}' is not present in repository")

        contents = tomli.loads(str(toml_contents[toml_file]))
        src_file_prefix = Path(toml_file).parent
        dst_file_prefix = src_file_prefix
        if "**" in contents["paths"][0]["reference"]:
            # localized file paths contain globs; we need that directory
            # structure to determine the files we need to fetch
            force_paths = await github_client.get_file_listing(str(src_file_prefix), branch=from_branch)
        else:
            force_paths = []

        for src_name in getL10nFilesFromToml(toml_file, contents, force_paths):
            dst_name = dst_file_prefix / src_name.relative_to(src_file_prefix)
            l10n_files.append(L10nFile(src_name=str(src_name), dst_name=str(dst_name)))

    # fetch l10n_files from `from_branch` in the gecko repo
    src_files = [f["src_name"] for f in l10n_files]
    log.info(f"fetching updated files from l10n repository: {src_files}")
    new_files = await github_client.get_files(src_files, branch=from_branch)

    # fetch l10n_files from gecko repo
    dst_files = [f["dst_name"] for f in l10n_files]
    log.info(f"fetching original files from l10n repository: {dst_files}")
    orig_files = await github_client.get_files(dst_files, branch=to_branch)

    diff = ""
    for l10n_file in l10n_files:
        if l10n_file["dst_name"] not in orig_files:
            log.warning(f"WEIRD: {l10n_file['dst_name']} not in dst_files, continuing anyways...")
            continue

        if l10n_file["src_name"] not in new_files:
            log.warning(f"WEIRD: {l10n_file['src_name']} not in src_files, continuing anyways...")
            continue

        orig_file = orig_files[l10n_file["dst_name"]]
        new_file = new_files[l10n_file["src_name"]]
        if orig_file == new_file:
            log.warning(f"old and new contents of {new_file} are the same, skipping bump...")
            continue

        diff += diff_contents(orig_file, new_file, l10n_file["dst_name"])

    if not diff:
        return {}

    with open(os.path.join(public_artifact_dir, "android-sync.diff"), "w+") as f:
        f.write(diff)

    log.info("adding android l10n sync! diff contents are:")
    log_file_contents(diff)

    commitmsg = f"Import translations from {from_branch}"
    return create_commit_action(commitmsg, diff)
