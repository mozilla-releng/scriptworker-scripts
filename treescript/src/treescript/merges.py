"""Treescript merge day functionality."""
import logging
import os
import shutil
import string
from datetime import date

import attr
from scriptworker_client.utils import makedirs

from treescript.l10n import l10n_bump
from treescript.mercurial import commit, get_revision, run_hg_command
from treescript.task import get_l10n_bump_info, get_merge_config, get_metadata_source_repo
from treescript.versionmanip import do_bump_version, get_version

log = logging.getLogger(__name__)


class BashFormatter(string.Formatter):
    """BashFormatter: Safer bash strings.

    Ignore things that are probably bash variables when formatting.

    For example, this will be passed back unchanged:
    "MOZ_REQUIRE_SIGNING=${MOZ_REQUIRE_SIGNING-0}"
    while still allowing us to have:
    "Tagging {current_major_version}"
    """

    def get_value(self, key, args, kwds):
        """If a value is not found, return the key."""
        if isinstance(key, str):
            return kwds.get(key, "{" + key + "}")
        else:
            return string.Formatter().get_value(key, args, kwds)


def replace(file_name, from_, to_):
    """Replace text in a file."""
    log.info("Replacing %s -> %s inside %s", from_, to_, file_name)
    with open(file_name) as f:
        text = f.read()
    new_text = text.replace(from_, to_)
    if text == new_text:
        raise ValueError(f"{file_name} does not contain {from_}")
    with open(file_name, "w") as f:
        f.write(new_text)


def touch_clobber_file(config, repo_path):
    """Update the clobber file in the root of the repo."""
    if not config["merge_day_clobber_file"]:
        log.info("merge_day_clobber_file not set, skipping clobber file update")
    else:
        log.info("Touching clobber file")
        clobber_file = os.path.join(repo_path, config["merge_day_clobber_file"])
        with open(clobber_file) as f:
            contents = f.read()
        new_contents = ""
        for line in contents.splitlines():
            line = line.strip()
            if line.startswith("#") or line == "":
                new_contents += f"{line}\n"
        new_contents = f"{new_contents}Merge day clobber {str(date.today())}"
        with open(clobber_file, "w") as f:
            f.write(new_contents)


def create_new_version(version_config, repo_path, source_repo):
    """Create the new version string used in file manipulation.

    Arguments:
        version_config (dict):
            {
                "filename": mandatory path,
                "new_suffix": string, default is to keep original.
                "version_bump": string, optional, enum 'major', 'minor'
            }

    Returns:
        string: new version string for file contents.
    """
    version = get_version(version_config["filename"], repo_path, source_repo)
    if version_config.get("version_bump") == "major":
        version = version.bump("major_number")
    elif version_config.get("version_bump") == "minor":
        version = version.bump("minor_number")
    if "new_suffix" in version_config:  # '' is a valid entry
        version = attr.evolve(version, is_esr=False, beta_number=None, is_nightly=False)
        version = f"{version}{version_config['new_suffix']}"
    else:
        version = f"{version}"
    log.info("New version is %s", version)
    return version


async def apply_rebranding(config, repo_path, merge_config, source_repo):
    """Apply changes to repo required for merge/rebranding."""
    log.info("Rebranding %s to %s", merge_config.get("from_branch"), merge_config.get("to_branch"))

    # Must collect this before any bumping.
    version = get_version(core_version_file(merge_config), repo_path, source_repo)
    # Used in file replacements, further down.
    format_options = {
        "current_major_version": version.major_number,
        "next_major_version": version.major_number + 1,
        "current_weave_version": version.major_number + 2,
        "next_weave_version": version.major_number + 3,  # current_weave_version + 1
    }

    if merge_config.get("version_files"):
        for version_config in merge_config["version_files"]:
            await do_bump_version(config, repo_path, [version_config["filename"]], create_new_version(version_config, repo_path, source_repo), source_repo)

    for f in merge_config.get("copy_files", list()):
        shutil.copyfile(os.path.join(repo_path, f[0]), os.path.join(repo_path, f[1]))

    # Cope with bash variables in strings that we don't want to
    # be formatted in Python. We do this by ignoring {vars} we
    # aren't given keys for.
    fmt = BashFormatter()
    for f, from_, to in merge_config.get("replacements", list()):
        from_ = fmt.format(from_, **format_options)
        to = fmt.format(to, **format_options)
        replace(os.path.join(repo_path, f), from_, to)

    touch_clobber_file(config, repo_path)


async def preserve_tags(config, repo_path, to_branch):
    """Preserve hg tags after debugsetparents."""
    tag_diff = await run_hg_command(config, "diff", "-r", to_branch, os.path.join(repo_path, ".hgtags"), "-U0", return_output=True, repo_path=repo_path)
    await run_hg_command(config, "revert", "-r", to_branch, os.path.join(repo_path, ".hgtags"), repo_path=repo_path)
    with open(os.path.join(repo_path, ".hgtags"), "a") as fh:
        # Skip four header lines
        for line in tag_diff.splitlines()[4:]:
            # We only care about additions.
            if not line.startswith("+"):
                continue
            line = line.lstrip("+")
            changeset, _ = line.split()
            # Check for bogus changeset
            if len(changeset) != 40:
                continue
            fh.write(f"{line}\n")
    status_out = await run_hg_command(config, "status", os.path.join(repo_path, ".hgtags"), return_output=True, repo_path=repo_path)
    if status_out:
        await commit(config, repo_path, "Preserve old tags after debusetparents. CLOSED TREE DONTBUILD a=release")


def core_version_file(merge_config):
    """Determine which file to query for the 'main' version.

    In a function to avoid duplication of the default value.
    """
    return merge_config.get("fetch_version_from", "browser/config/version.txt")


async def pull_branches(config, repo_path, upstream_repo, from_branch, to_branch):
    """Pull the branches needed for this merge operation.

    If upstream_repo is set (eg. to mozilla-unified) then it provides everything
    that is needed.
    When upstream_repo is not set (eg. for comm repositories) then separate
    pulls are needed to ensure that the revisions that need to be operated on
    are available locally. The branch names from firefoxtree are used to do this.
    """
    if upstream_repo:
        await run_hg_command(config, "pull", upstream_repo, repo_path=repo_path)
    else:
        if to_branch:
            await run_hg_command(config, "pull", to_branch, repo_path=repo_path)
        if from_branch:
            await run_hg_command(config, "pull", from_branch, repo_path=repo_path)


# do_merge {{{1
async def do_merge(config, task, repo_path):
    """Perform a merge day operation.

    This function takes its inputs from task's payload.

    Args:
        config (dict): the running config
        task (dict): the running task
        repo_path (str): the source directory

    Raises:
        TaskverificationError: from get_merge_config if the payload is invalid.

    Returns:
        list: A list of the branches that need pushing, and the corresponding revision.
              This is unlike other actions as the list of outgoing changes is
              not related to the number of commands we've performed, but we do need
              to know which branches to push.
    """
    merge_config = get_merge_config(task)
    source_repo = get_metadata_source_repo(task)

    upstream_repo = config["upstream_repo"]
    from_branch = merge_config.get("from_branch")
    to_branch = merge_config.get("to_branch")

    await pull_branches(config, repo_path, upstream_repo, from_branch, to_branch)

    # Used if end_tag is set.
    await run_hg_command(config, "up", "-C", to_branch, repo_path=repo_path)
    to_fx_major_version = get_version(core_version_file(merge_config), repo_path, source_repo).major_number
    base_to_rev = await get_revision(config, repo_path, branch=to_branch)

    if from_branch:
        await run_hg_command(config, "up", "-C", from_branch, repo_path=repo_path)
        base_from_rev = await get_revision(config, repo_path, branch=from_branch)
        from_fx_major_version = get_version(core_version_file(merge_config), repo_path, source_repo).major_number
        if from_fx_major_version == to_fx_major_version:
            log.info("Skipping merge: %s and %s versions already match (%s)", from_branch, to_branch, from_fx_major_version)
            return []

    base_tag = merge_config.get("base_tag")
    if base_tag:
        base_tag = base_tag.format(major_version=get_version(core_version_file(merge_config), repo_path, source_repo).major_number)
        tag_message = f"No bug - tagging {base_from_rev} with {base_tag} a=release DONTBUILD CLOSED TREE"
        await run_hg_command(config, "tag", "-m", tag_message, "-r", base_from_rev, "-f", base_tag, repo_path=repo_path)

    tagged_from_rev = await get_revision(config, repo_path, branch=".")

    # TODO This shouldn't be run on esr, according to old configs.
    # perhaps: hg push -r bookmark("release") esrNN
    # Perform the kludge-merge.
    if merge_config.get("merge_old_head", False):
        await run_hg_command(config, "debugsetparents", tagged_from_rev, base_to_rev, repo_path=repo_path)
        await commit(config, repo_path, "Merge old head via |hg debugsetparents {} {}| CLOSED TREE DONTBUILD a=release".format(tagged_from_rev, base_to_rev))
        await preserve_tags(config, repo_path, to_branch)

    end_tag = merge_config.get("end_tag")  # tag the end of the to repo
    if end_tag:
        end_tag = end_tag.format(major_version=to_fx_major_version)
        tag_message = f"No bug - tagging {base_to_rev} with {end_tag} a=release DONTBUILD CLOSED TREE"
        await run_hg_command(config, "tag", "-m", tag_message, "-r", base_to_rev, "-f", end_tag, repo_path=repo_path)

    await _maybe_bump_l10n(config, task, repo_path)
    await apply_rebranding(config, repo_path, merge_config, source_repo)

    diff_output = await run_hg_command(config, "diff", repo_path=repo_path, return_output=True)
    path = os.path.join(config["artifact_dir"], "public", "logs", "{}.diff".format(to_branch))
    makedirs(os.path.dirname(path))
    with open(path, "w") as fh:
        fh.write(diff_output)

    await commit(config, repo_path, "Update configs. IGNORE BROKEN CHANGESETS CLOSED TREE NO BUG a=release ba=release")
    push_revision_to = await get_revision(config, repo_path, branch=".")

    # Do we need to perform multiple pushes for the push stage? If so, return
    # what to do.
    desired_pushes = list()
    if merge_config.get("from_repo"):
        desired_pushes.append((merge_config["from_repo"], tagged_from_rev))
    if merge_config.get("to_repo"):
        desired_pushes.append((merge_config["to_repo"], push_revision_to))
    return desired_pushes


async def _maybe_bump_l10n(config, task, repo_path):
    if get_l10n_bump_info(task, raise_on_empty=False):
        await l10n_bump(config, task, repo_path)
        output = await run_hg_command(config, "log", "--patch", "--verbose", "-r", ".", repo_path=repo_path, return_output=True, expected_exit_codes=(0, 1))
        path = os.path.join(config["artifact_dir"], "public", "logs", "l10n_bump.diff")
        makedirs(os.path.dirname(path))
        with open(path, "w") as fh:
            fh.write(output)
