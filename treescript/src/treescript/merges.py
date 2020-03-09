"""Treescript merge day functionality."""
import logging
import os
import shutil

import attr

from scriptworker_client.utils import makedirs, run_command
from treescript.mercurial import get_revision, run_hg_command
from treescript.task import get_merge_config
from treescript.versionmanip import do_bump_version, get_version

log = logging.getLogger(__name__)


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


def touch_clobber_file(repo_path):
    """Update the clobber file in the root of the repo."""
    log.info("Touching clobber file")
    clobber_file = os.path.join(repo_path, "CLOBBER")
    with open(clobber_file) as f:
        contents = f.read()
    new_contents = ""
    for line in contents.splitlines():
        line = line.strip()
        if line.startswith("#") or line == "":
            new_contents += f"{line}\n"
    new_contents += "Merge day clobber"
    with open(clobber_file, "w") as f:
        f.write(new_contents)


async def apply_rebranding(config, repo_path, merge_config):
    """Apply changes to repo required for merge/rebranding."""
    log.info("Rebranding %s to %s", merge_config.get("from_branch"), merge_config.get("to_branch"))
    if merge_config.get("version_files"):
        current_version = get_version("browser/config/version.txt", repo_path)
        next_version = f"{current_version.major_number}.{current_version.minor_number}"

        await do_bump_version(config, repo_path, merge_config["version_files"], next_version)
    if merge_config.get("version_files_suffix"):
        current_version = get_version("browser/config/version.txt", repo_path)
        current_version = attr.evolve(current_version, is_esr=False, beta_number=None, is_nightly=False)
        next_version = f"{current_version}{merge_config.get('version_suffix')}"

        await do_bump_version(config, repo_path, merge_config["version_files_suffix"], next_version)

    for f in merge_config.get("copy_files", list()):
        shutil.copyfile(os.path.join(repo_path, f[0]), os.path.join(repo_path, f[1]))

    for f, from_, to in merge_config.get("replacements", list()):
        replace(os.path.join(repo_path, f), from_, to)

    touch_clobber_file(repo_path)


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

    from_branch = merge_config.get("from_branch")
    to_branch = merge_config.get("to_branch")

    await run_hg_command(config, "pull", "https://hg.mozilla.org/mozilla-unified", repo_path=repo_path)

    await run_hg_command(config, "up", "-C", from_branch, repo_path=repo_path)

    base_from_rev = await get_revision(config, repo_path, branch=from_branch)

    base_tag = merge_config["base_tag"].format(major_version=get_version("browser/config/version.txt", repo_path).major_number)

    tag_message = f"No bug - tagging {os.path.basename(repo_path)} with {base_tag} a=release DONTBUILD CLOSED TREE"
    await run_hg_command(config, "tag", "-m", '"{}"'.format(tag_message), "-r", base_from_rev, "-f", base_tag, repo_path=repo_path)

    tagged_from_rev = await get_revision(config, repo_path, branch=".")

    # TODO This shouldn't be run on esr, according to old configs.
    # perhaps: hg push -r bookmark("release") esrNN
    # Perform the kludge-merge.
    if merge_config.get("merge_old_head", False):
        await run_hg_command(config, "debugsetparents", tagged_from_rev, to_branch, repo_path=repo_path)
        await run_hg_command(
            config,
            "commit",
            "-m",
            "Merge old head via |hg debugsetparents {} {}| CLOSED TREE DONTBUILD a=release".format(tagged_from_rev, to_branch),
            repo_path=repo_path,
        )
        # Preserve tags.
        patch_file = os.path.join(os.path.dirname(repo_path), "patch_file")
        tag_diff = await run_hg_command(config, "diff", "-r", to_branch, os.path.join(repo_path, ".hgtags"), "-U9", return_output=True, repo_path=repo_path)
        with open(patch_file, "w") as fh:
            fh.write(tag_diff)
        await run_command(["patch", "-R", "-p1", patch_file], cwd=repo_path)
        os.unlink(patch_file)
        with open(os.path.join(repo_path, ".hgtags"), "a") as fh:
            # Skip four header lines
            for line in tag_diff.splitlines()[4:]:
                # We only care about additions.
                if not line.startswith("+"):
                    continue
                line = line.replace("+", "")
                changeset, _ = line.split()
                # Check for bogus changeset
                if len(changeset) != 40:
                    continue
                fh.write(f"{line}\n")
        status_out = await run_hg_command(config, "status", os.path.join(repo_path, ".hgtags"), return_output=True, repo_path=repo_path)
        if status_out:
            await run_hg_command(config, "commit", "-m", "Preserve old tags after debusetparents. CLOSED TREE DONTBUILD a=release", repo_path=repo_path)
        else:
            log.info("No changes to .hgtags, not performing commit.")

    end_tag = merge_config.get("end_tag")  # tag the end of the to repo
    if end_tag:
        to_fx_major_version = get_version("browser/config/version.txt", repo_path).major_number
        base_to_rev = await get_revision(config, repo_path, branch=to_branch)
        end_tag = end_tag.format(major_version=to_fx_major_version)
        tag_message = f"No bug - tagging {os.path.basename(repo_path)} with {end_tag} a=release DONTBUILD CLOSED TREE"
        await run_hg_command(config, "tag", "-m", f'"{tag_message}"', "-r", base_to_rev, "-f", end_tag, repo_path=repo_path)

    await apply_rebranding(config, repo_path, merge_config)

    diff_output = await run_hg_command(config, "diff", repo_path=repo_path, return_output=True)
    path = os.path.join(config["artifact_dir"], "public", "logs", "{}.diff".format(to_branch))
    makedirs(os.path.dirname(path))
    with open(path, "w") as fh:
        fh.write(diff_output)

    await run_hg_command(config, "commit", "-m", "Update configs. IGNORE BROKEN CHANGESETS CLOSED TREE NO BUG a=release ba=release", repo_path=repo_path)
    push_revision_to = await get_revision(config, repo_path, branch=".")

    # Do we need to perform multiple pushes for the push stage? If so, return
    # what to do.
    desired_pushes = list()
    if merge_config.get("from_repo"):
        desired_pushes.append((merge_config["from_repo"], tagged_from_rev))
    if merge_config.get("to_repo"):
        desired_pushes.append((merge_config["to_repo"], push_revision_to))
    return desired_pushes
