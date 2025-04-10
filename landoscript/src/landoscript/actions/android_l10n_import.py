import logging
import os.path
from pathlib import Path

import tomli
from moz.l10n.paths import L10nConfigPaths, get_android_locale
from scriptworker.client import TaskVerificationError

from landoscript.lando import create_commit_action
from landoscript.util.diffs import diff_contents
from landoscript.util.log import log_file_contents
from scriptworker_client.github import extract_github_repo_owner_and_name
from scriptworker_client.github_client import GithubClient

log = logging.getLogger(__name__)


async def run(github_client, github_config, public_artifact_dir, branch, android_l10n_import_info):
    log.info("Preparing to import android l10n changesets.")

    l10n_repo_url = android_l10n_import_info.get("from_repo_url")
    if not l10n_repo_url:
        raise TaskVerificationError("Cannot bump l10n revisions from github repo without an l10n_repo_url")
    l10n_owner, l10n_repo = extract_github_repo_owner_and_name(l10n_repo_url)

    async with GithubClient(github_config, l10n_owner, l10n_repo) as l10n_github_client:
        toml_files = [info["toml_path"] for info in android_l10n_import_info["toml_info"]]
        toml_contents = await l10n_github_client.get_files(toml_files)
        src_repo_files = []
        dst_repo_files = []

        for info in android_l10n_import_info["toml_info"]:
            toml_file = info["toml_path"]
            contents = toml_contents[toml_file]
            src_file_prefix = Path(toml_file).parent
            dst_file_prefix = Path(info["dest_path"])

            for f in getL10nFilesFromToml(contents):
                src_repo_files.append(str(src_file_prefix / f))
                dst_repo_files.append(str(dst_file_prefix / f))

        # fetch l10n_files from android-l10n
        src_files = await l10n_github_client.get_files(src_repo_files)
        # fetch l10n_files from gecko repo
        dst_files = await github_client.get_files(dst_repo_files)

        # TODO: do we need to do anything special to handle added or removed files?
        diff = ""
        for fn in src_files:
            diff_contents(src_files[fn], dst_files[fn], fn)

        with open(os.path.join(public_artifact_dir, "android-import.diff"), "w+") as f:
            f.write(diff)

        log.info("adding android l10n import! diff contents are:")
        log_file_contents(diff)

        commitmsg = "somtehing"
        return create_commit_action(commitmsg, diff)


def getL10nFilesFromToml(toml_contents):
    """Extract list of localized files from project configuration (TOML)"""

    def load(_):
        return tomli.loads(toml_contents)

    project_config_paths = L10nConfigPaths("", cfg_load=load, locale_map={"android_locale": get_android_locale})

    l10n_files = []
    locales = list(project_config_paths.all_locales)
    locales.sort()

    tgt_paths = [tgt_path for _, tgt_path in project_config_paths.all()]
    for locale in locales:
        print(f"Creating list of files for locale: {locale}.")
        # Exclude missing files
        for tgt_path in tgt_paths:
            path = project_config_paths.format_target_path(tgt_path, locale)
            l10n_files.append(path)

    return l10n_files
