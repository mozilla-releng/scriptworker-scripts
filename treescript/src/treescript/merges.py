"""Treescript merge day functionality."""
import os

import shutil
import logging

from treescript.exceptions import TaskVerificationError
from treescript.mercurial import get_revision, run_hg_command
from treescript.task import get_merge_flavor
from treescript.versionmanip import do_bump_version, get_version

from treescript.merge_config import merge_configs
from scriptworker_client.utils import makedirs

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
    log.info(
        "Rebranding %s to %s",
        merge_config.get("from_branch"),
        merge_config.get("to_branch"),
    )
    if merge_config.get("version_files"):
        current_version = get_version("browser/config/version.txt", repo_path)
        next_version = f"{current_version.major_number}.{current_version.minor_number}"

        await do_bump_version(
            config,
            repo_path,
            merge_config["version_files"],
            next_version,
            dontbuild=True,
            commit=False,
        )
    if merge_config.get("version_files_suffix"):
        current_version = get_version("browser/config/version.txt", repo_path)
        next_version = f"{current_version.major_number}.{current_version.minor_number}{merge_config.get('version_suffix')}"

        await do_bump_version(
            config,
            repo_path,
            merge_config["version_files_suffix"],
            next_version,
            dontbuild=True,
            commit=False,
        )

    for f in merge_config.get("copy_files", list()):
        shutil.copyfile(
            os.path.join(repo_path, f["src"]), os.path.join(repo_path, f["dst"])
        )

    for f, from_, to in merge_config.get("replacements", list()):
        replace(os.path.join(repo_path, f), from_, to)

    if merge_config.get("remove_locales"):
        log.info("Removing locales")
        remove_locales(
            os.path.join(repo_path, "browser/locales/shipped-locales"),
            merge_config["remove_locales"],
        )
    touch_clobber_file(repo_path)


def remove_locales(file_name, removals):
    """Remove locales from shipped-locales (mozilla-release only)."""
    with open(file_name) as f:
        contents = f.readlines()
    new_contents = ""
    for line in contents:
        locale = line.split()[0]
        if locale not in removals:
            new_contents += line
        else:
            log.info("Removed locale: %s" % locale)
    with open(file_name, "w") as f:
        f.write(new_contents)


# do_merge {{{1
async def do_merge(config, task, repo_path):
    """Perform a merge day operation.

    This function takes its inputs from task by using the ``get_merge_flavor``
    function from treescript.task. Using `merge_info` to determine which
    set of modifications to make. The modifications are stored in the
    scriptworker to provide version control.

    Args:
        config (dict): the running config
        task (dict): the running task
        repo_path (str): the source directory

    Raises:
        TaskverificationError: if a merge flavor is not recognised..

    Returns:
        list: A list of the branches that need pushing, and the corresponding revision.
              This is unlike other actions as the list of outgoing changes is
              not related to the number of commands we've performed, but we do need
              to know which branches to push.
    """
    flavor = get_merge_flavor(task)

    if flavor not in merge_configs:
        raise TaskVerificationError(
            "Unknown configuration for merge day flavor {}".format(flavor)
        )

    from_branch = merge_configs[flavor].get("from_branch")
    to_branch = merge_configs[flavor].get("to_branch")

    log.info("hg pull %s", repo_path)
    await run_hg_command(config, "pull", repo_path=repo_path)

    log.info("hg up -C %s", from_branch)
    await run_hg_command(config, "up", "-C", from_branch, repo_path=repo_path)

    base_from_rev = await get_revision(config, repo_path)
    log.info("base_from_rev %s", base_from_rev)

    base_tag = merge_configs[flavor]["base_tag"].format(
        major_version=get_version("browser/config/version.txt", repo_path).major_number
    )

    tag_message = f"No bug - tagging {os.path.basename(repo_path)} with {base_tag} a=release DONTBUILD CLOSED TREE"
    log.info("Tagging: %s", tag_message)
    await run_hg_command(
        config,
        "tag",
        "-m",
        '"{}"'.format(tag_message),
        "-r",
        base_from_rev,
        "-u",
        config["hg_ssh_user"],
        "-f",
        base_tag,
        repo_path=repo_path,
    )

    # TODO This shouldn't be run on esr, according to old configs.
    # perhaps: hg push -r bookmark("release") esrNN
    # Perform the kludge-merge.
    if merge_configs[flavor].get("require_debugsetparents", False):
        log.info("hg debugsetparents %s %s(%s)", to_branch, base_from_rev, from_branch)
        await run_hg_command(
            config, "debugsetparents", to_branch, base_from_rev, repo_path=repo_path
        )

        log.info("hg commit %s <- %s", to_branch, from_branch)
        await run_hg_command(
            config,
            "commit",
            "-m",
            "Merge old head via |hg debugsetparents {} {}| CLOSED TREE DONTBUILD a=release".format(
                to_branch, from_branch
            ),
            repo_path=repo_path,
        )

    log.info("hg up -C %s", to_branch)
    await run_hg_command(config, "up", "-C", to_branch, repo_path=repo_path)

    log.info("Adding end tag")
    end_tag = merge_configs[flavor].get("end_tag")  # tag the end of the to repo
    if end_tag:
        to_fx_major_version = get_version(
            "browser/config/version.txt", repo_path
        ).major_number
        base_to_rev = await get_revision(config, repo_path)
        end_tag = end_tag.format(major_version=to_fx_major_version)
        await run_hg_command(
            config,
            "tag",
            "-m",
            end_tag,
            "-r",
            base_to_rev,
            "-u",
            config["hg_ssh_user"],
            "-f",
            end_tag,
            repo_path=repo_path,
        )

    await apply_rebranding(config, repo_path, merge_configs[flavor])

    diff_output = await run_hg_command(
        config, "diff", repo_path=repo_path, return_output=True
    )
    path = os.path.join(
        config["artifact_dir"], "public", "logs", "{}.diff".format(to_branch)
    )
    makedirs(os.path.dirname(path))
    with open(path, "w") as fh:
        fh.write(diff_output)

    await run_hg_command(
        config,
        "commit",
        "-u",
        config["hg_ssh_user"],
        "-m",
        "Update configs. IGNORE BROKEN CHANGESETS CLOSED TREE NO BUG a=release ba=release",
        repo_path=repo_path,
    )
    push_revision_to = await get_revision(config, repo_path)

    # Do we need to perform multiple pushes for the push stage? If so, return
    # what to do.
    if merge_configs[flavor].get("push_repositories"):
        return [
            (merge_configs[flavor]["push_repositories"]["from"], base_from_rev),
            (merge_configs[flavor]["push_repositories"]["to"], push_revision_to),
        ]
