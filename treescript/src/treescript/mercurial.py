"""Treescript mercurial functions."""
import logging
import os
import sys
import tempfile

from scriptworker_client.utils import load_json_or_yaml, makedirs, run_command
from treescript.exceptions import CheckoutError, FailedSubprocess, PushError
from treescript.task import DONTBUILD_MSG, get_branch, get_dontbuild, get_source_repo, get_tag_info

# https://www.mercurial-scm.org/repo/hg/file/tip/tests/run-tests.py#l1040
# For environment vars.

HGRCPATH = os.path.join(os.path.dirname(__file__), "data", "hgrc")
ROBUSTCHECKOUT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "py2", "robustcheckout.py"))
TAG_MSG = "No bug - Tagging {revision} with {tags} a=release CLOSED TREE"

log = logging.getLogger(__name__)


# build_hg_command {{{1
def build_hg_command(config, *args):
    """Generate a mercurial command to run.

    See-Also ``build_hg_environment``

    Args:
        config (dict): the running config.
        *args: the remaining args to pass to the hg command

    Returns:
        list: the hg command to run.

    """
    hg = config["hg"]
    if not isinstance(hg, (list, tuple)):
        hg = [hg]
    robustcheckout_args = [
        "--config",
        "extensions.robustcheckout={}".format(ROBUSTCHECKOUT_PATH),
        "--config",
        "extensions.purge=",
        "--config",
        "extensions.strip=",
    ]
    return hg + [*robustcheckout_args, *args]


# build_hg_environment {{{1
def build_hg_environment():
    """Generate an environment suitable for running mercurial programatically.

    This function sets the hgrc to one provided in the package and ensures
    environment variables which affect HG are defined in a stable way.

    See-Also ``build_hg_command``, ``run_hg_command``

    Returns:
        list: the environment to use.

    """
    env = os.environ.copy()
    env["HGRCPATH"] = HGRCPATH
    env["HGEDITOR"] = '"' + sys.executable + '"' + ' -c "import sys; sys.exit(0)"'
    env["HGMERGE"] = "internal:merge"
    env["HGENCODING"] = "utf-8"
    env["HGPLAIN"] = "1"
    env["LANG"] = env["LC_ALL"] = env["LANGUAGE"] = "C"
    env["TZ"] = "GMT"
    # List found at
    # https://www.mercurial-scm.org/repo/hg/file/ab239e3de23b/tests/run-tests.py#l1076
    for k in ("HG HGPROF CDPATH GREP_OPTIONS http_proxy no_proxy " + "HGPLAINEXCEPT EDITOR VISUAL PAGER NO_PROXY CHGDEBUG").split():
        if k in env:
            del env[k]
    return env


# run_hg_command {{{1
async def run_hg_command(config, *args, repo_path=None, exception=FailedSubprocess, return_output=False, **kwargs):
    """Run a mercurial command.

    See-Also ``build_hg_environment``, ``build_hg_command``

    Args:
        config (dict): the running config.
        *args: the remaining args to pass to the hg command.
        repo_path (str, optional): the local repo to use, if specified.
            Defaults to ``None``.
        exception (Exception, optional): the exception to raise on error.
            Defaults to ``FailedSubprocess``.
        return_output (bool, optional): return the output of the command
            if ``True``. Defaults to ``False``.
        **kwargs: the remaining kwargs to pass to the hg command.

    Returns:
        None: if ``return_output`` is ``False``
        str: the output if ``return_output`` is ``True``

    """
    command = build_hg_command(config, *args)
    env = build_hg_environment()
    return_value = None
    if repo_path:
        command.extend(["-R", repo_path])
    with tempfile.NamedTemporaryFile() as fp:
        log_path = fp.name
        await run_command(command, env=env, exception=exception, log_path=log_path, **kwargs)
        if return_output:
            with open(log_path, "r") as fh:
                return_value = fh.read()

    return return_value


# log_mercurial_version {{{1
async def log_mercurial_version(config):
    """Run mercurial '-v version' to get used version into logs.

    Args:
        config (dict): the running config.

    """
    log.info(await run_hg_command(config, "-v", "version", return_output=True))


# validate_robustcheckout_works {{{1
async def validate_robustcheckout_works(config):
    """Validate that the robustcheckout extension works.

    This works by trying to run 'hg robustcheckout -q --help' on
    hg as defined by our config.

    Args:
        config (dict): the running config.

    Returns:
        bool: True if robustcheckout seems to work, False otherwise.

    """
    try:
        await run_hg_command(config, "robustcheckout", "-q", "--help")
        return True
    except FailedSubprocess:
        return False


# checkout_repo {{{1
async def checkout_repo(config, task, repo_path):
    """Perform a clone via robustcheckout, at ${directory}/src.

    This function will perform a clone via robustcheckout, using hg's share extension
    for a cache at 'config['hg_share_base_dir']' that robustcheckout will
    populate if necessary.

    Robustcheckout will retry network operations at most 3 times (robustcheckout's default)
    before giving up and causing FailedSubprocess to be raised.

    Args:
        config (dict): the running config.
        task (dict): the running task.
        repo_path (str): The directory to place the resulting clone.

    Raises:
        CheckoutError: if the clone attempt doesn't succeed.

    """
    share_base = config["hg_share_base_dir"]
    upstream_repo = config["upstream_repo"]
    source_repo = get_source_repo(task)
    # branch default is used to pull tip of the repo at checkout time
    branch = get_branch(task, "default")
    await run_hg_command(
        config, "robustcheckout", source_repo, repo_path, "--sharebase", share_base, "--upstream", upstream_repo, "--branch", branch, exception=CheckoutError
    )


# do_tagging {{{1
async def get_existing_tags(config, repo_path):
    """Get the existing tags in a mercurial repo.

    Args:
        config (dict): the running config
        repo_path (str): the path to the repo

    Returns:
        dict: ``{tag1: revision1, tag2: revision2, ...}``

    """
    existing_tags = {}
    output = load_json_or_yaml(await run_hg_command(config, "tags", "--template=json", repo_path=repo_path, return_output=True))
    for tag_info in output:
        existing_tags[tag_info["tag"]] = tag_info["node"]
    return existing_tags


async def check_tags(config, tag_info, repo_path):
    """Check to see if ``tag_names`` already exist in ``repo_path``.

    Return the subset of tags that don't exist.

    Args:
        config (dict): the running config
        tag_info (dict): the tags and revision to check
        repo_path (str): the path of the repository on disk

    Returns:
        list: the subset of tags that don't already exist on the target
            revision

    """
    tags = []
    existing_tags = await get_existing_tags(config, repo_path)
    revision = tag_info["revision"]
    for tag in tag_info["tags"]:
        if tag in existing_tags:
            if revision == existing_tags[tag]:
                log.info("Tag %s already exists on revision %s. Skipping...", tag, revision)
                continue
            else:
                log.warning("Tag %s exists on mismatched revision %s! Retagging...", tag, revision)
        tags.append(tag)
    return tags


async def get_revision(config, repo_path):
    """Obtain the current revision."""
    return await run_hg_command(config, "parent", "--template", "{node}", return_output=True, repo_path=repo_path)


async def do_tagging(config, task, repo_path):
    """Perform tagging, at ${repo_path}/src.

    This function will perform a mercurial tag, on 'default' head of target repository.
    It will tag the revision specified in the tag_info portion of the task payload, using
    the specified tags in that payload.

    Tags are forced to be created at the specified revision if they already existed.

    This function has the side affect of pulling the specified revision from the
    destination repository. This feature exists because mozilla-unified does not
    contain relbranches, though some releases are created on relbranches, so we must ensure
    the desired revision to tag is known to the local repository.

    Args:
        config (dict): the running config.
        task (dict): the running task.
        repo_path (str): The directory to place the resulting clone.

    Raises:
        FailedSubprocess: if the tag attempt doesn't succeed.

    Returns:
        int: the number of tags created.

    """
    tag_info = get_tag_info(task)
    desired_tags = await check_tags(config, tag_info, repo_path)
    if not desired_tags:
        log.info("No unique tags to add; skipping tagging.")
        return 0
    desired_rev = tag_info["revision"]
    dontbuild = get_dontbuild(task)
    source_repo = get_source_repo(task)
    commit_msg = TAG_MSG.format(revision=desired_rev, tags=", ".join(desired_tags))
    if dontbuild:
        commit_msg += DONTBUILD_MSG
    log.info("Pulling {revision} from {repo} explicitly.".format(revision=desired_rev, repo=source_repo))
    await run_hg_command(config, "pull", "-r", desired_rev, source_repo, repo_path=repo_path)
    log.info(commit_msg)
    await run_hg_command(config, "tag", "-m", commit_msg, "-r", desired_rev, "-f", *desired_tags, repo_path=repo_path)  # Todo only force if needed
    return 1


# _count_outgoing {{{1
def _count_outgoing(output):
    """Count the number of outgoing hg changesets from `hg outgoing`.

    There's a possibility of over-counting, if someone starts their commit
    message line with `changeset: `, but since we currently know all of our
    expected commit messages, we shouldn't have any false positives here.

    """
    count = 0
    for line in output.splitlines():
        if line.startswith("changeset: "):
            count += 1
    return count


# log_outgoing {{{1
async def log_outgoing(config, task, repo_path):
    """Run `hg out` against the current revision in the repository.

    This logs current changes that will be pushed (or would have been, if dry-run)

    Args:
        config (dict): the running config
        task (dict): the running task
        repo_path (str): the source repo path

    Raises:
        FailedSubprocess: on failure

    Returns:
        int: the number of outgoing changesets

    """
    source_repo = get_source_repo(task)
    log.info("outgoing changesets..")
    num_changesets = 0
    output = await run_hg_command(config, "out", "-vp", "-r", ".", source_repo, repo_path=repo_path, return_output=True, expected_exit_codes=(0, 1))
    if output:
        path = os.path.join(config["artifact_dir"], "public", "logs", "outgoing.diff")
        makedirs(os.path.dirname(path))
        with open(path, "w") as fh:
            fh.write(output)
        num_changesets = _count_outgoing(output)
    return num_changesets


# strip_outgoing {{{1
async def strip_outgoing(config, task, repo_path):
    """Strip all unpushed outgoing revisions and purge the changes.

    This is something we should do on failed pushes.

    Args:
        config (dict): the running config
        task (dict): the running task
        repo_path (str): the path to the repo

    Raises:
        FailedSubprocess: on error

    """
    log.info("Purging %s", repo_path)
    # `hg strip` will abort with an exit code of 255 if the repo is clean.
    await run_hg_command(config, "strip", "--no-backup", "outgoing()", repo_path=repo_path, exception=None, expected_exit_codes=(0, 255))
    await run_hg_command(config, "up", "-C", "-r", ".", repo_path=repo_path)
    await run_hg_command(config, "purge", "--all", repo_path=repo_path)


# push {{{1
async def push(config, task, repo_path, source_repo=None, revision=None):
    """Run `hg push` against the current source repo.

    Args:
        config (dict): the running config
        task (dict): the running task
        repo_path (str): the source repo path

    Raises:
        PushError: on failure

    """
    if not source_repo:
        source_repo = get_source_repo(task)
    source_repo_ssh = source_repo.replace("https://", "ssh://")
    ssh_username = config.get("hg_ssh_user")
    ssh_key = config.get("hg_ssh_keyfile")
    ssh_opt = []
    if ssh_username or ssh_key:
        ssh_opt = ["-e", "ssh"]
        if ssh_username:
            ssh_opt[1] += " -l %s" % ssh_username
        if ssh_key:
            ssh_opt[1] += " -i %s" % ssh_key
    log.info("Pushing local changes to {}".format(source_repo_ssh))
    try:
        await run_hg_command(config, "push", *ssh_opt, "-r", revision if revision else ".", "-v", source_repo_ssh, repo_path=repo_path, exception=PushError)
    except PushError as exc:
        log.warning("Hit PushError %s", str(exc))
        await strip_outgoing(config, task, repo_path)
        raise
