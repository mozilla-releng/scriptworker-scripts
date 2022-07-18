"""Treescript git functions."""
import logging
import os

from git import Actor, PushInfo, Repo
from scriptworker_client.github import extract_github_repo_ssh_url
from scriptworker_client.utils import get_single_item_from_sequence, makedirs

from treescript.exceptions import PushError, TaskVerificationError
from treescript.task import get_branch, get_source_repo, get_ssh_user

log = logging.getLogger(__name__)


async def checkout_repo(config, task, repo_path):
    """Perform a git clone at ${directory}/src.

    This function will perform a git clone. It will also checkout to the right branch,
    if provided in the task definition.

    Args:
        config (dict): the running config.
        task (dict): the running task.
        repo_path (str): The directory to place the resulting clone.

    Raises:
        TaskVerificationError: if the branch does not exist upstream.

    """
    source_repo = get_source_repo(task)
    if os.path.exists(repo_path):
        log.info("Reusing existing repo_path: {}".format(repo_path))
        repo = Repo(repo_path)
    else:
        log.info('Cloning source_repo "{}" to repo_path: {}'.format(source_repo, repo_path))
        repo = Repo.clone_from(
            source_repo,
            repo_path,
        )

    branch = get_branch(task)
    if branch:
        # GitPython cannot simply `git checkout` to right upstream branch. We have to manually
        # create a new branch and manually set the upstream branch
        log.info('Checking out branch "{}"'.format(branch))
        remote_branches = repo.remotes.origin.fetch()
        remote_branches_names = [fetch_info.name for fetch_info in remote_branches]
        remote_branch = get_single_item_from_sequence(
            remote_branches_names,
            condition=lambda remote_branch_name: remote_branch_name == _get_upstream_branch_name(branch),
            ErrorClass=TaskVerificationError,
            no_item_error_message="Branch does not exist on remote repo",
            too_many_item_error_message="Too many branches with that name",
        )

        repo.create_head(branch, remote_branch)
        repo.branches[branch].checkout()
    else:
        log.warning("No branch provided in the task payload. Staying on the default one")


async def get_existing_tags(config, repo_path):
    """Not implemented."""
    raise NotImplementedError()


async def check_tags(config, tag_info, repo_path):
    """Not implemented."""
    raise NotImplementedError()


async def get_revision(config, repo_path, branch):
    """Not implemented."""
    raise NotImplementedError()


async def do_tagging(config, task, repo_path):
    """Not implemented."""
    raise NotImplementedError()


async def log_outgoing(config, task, repo_path):
    """Log current changes that will be pushed (or would have been, if dry-run).

    Args:
        config (dict): the running config
        task (dict): the running task
        repo_path (str): the source repo path

    Returns:
        int: the number of outgoing changesets

    """
    log.info("Outgoing changesets...")

    repo = Repo(repo_path)
    branch = get_branch(task, "master")

    upstream_branch = _get_upstream_branch_name(branch)
    upstream_to_local_branch_interval = f"{upstream_branch}..{branch}"
    log.debug("Checking the number of changesets between these 2 references: {}".format(upstream_to_local_branch_interval))
    num_changesets = len(list(repo.iter_commits(upstream_to_local_branch_interval)))
    diff = repo.git.diff(upstream_branch)

    if diff:
        path = os.path.join(config["artifact_dir"], "public", "logs", "outgoing.diff")
        makedirs(os.path.dirname(path))
        with open(path, "w") as fh:
            fh.write(diff)

    log.info("Found {} new changesets".format(num_changesets))
    return num_changesets


async def strip_outgoing(config, task, repo_path):
    """Strip all unpushed outgoing revisions and purge the changes.

    This is something we should do on failed pushes.

    Args:
        config (dict): the running config
        task (dict): the running task
        repo_path (str): the path to the repo

    """
    repo = Repo(repo_path)
    branch = get_branch(task, "master")

    log.info("Resetting repo state to match upstream's...")
    repo.head.reset(commit=_get_upstream_branch_name(branch), working_tree=True)
    repo.git.clean("-fdx")
    log.info("Repo state reset.")


def _get_upstream_branch_name(branch):
    return "origin/{}".format(branch)


async def commit(config, repo_path, commit_msg):
    """Run `git add --all && git commit` against the current source repo.

    Args:
        config (dict): the running config
        repo_path (str): the source repo path
        commit_msg (str): the commit message
    """
    repo = Repo(repo_path)
    # XXX repo.index.add(["."]) adds files in the .git folder. It's a known issue
    # https://github.com/gitpython-developers/GitPython/issues/375
    repo.git.add(all=True)

    ssh_config = config.get("git_ssh_config", {}).get("default", {})
    email_address = ssh_config["emailAddress"]
    treescript_actor = Actor("Mozilla Releng Treescript", email_address)
    log.info("Adding every local change and committing them...")
    repo.index.commit(commit_msg, author=treescript_actor, committer=treescript_actor)
    log.info("Changes committed.")


async def push(config, task, repo_path, target_repo):
    """Run `git push` against the current source repo.

    Args:
        config (dict): the running config
        task (dict): the running task
        repo_path (str): the source repo path
        target_repo (str): Destination repository url
        revision (str): A specific revision to push
    Raises:
        PushError: on failure
    """
    ssh_config = config.get("git_ssh_config", {}).get(get_ssh_user(task), {})
    ssh_key = ssh_config.get("keyfile")
    git_ssh_cmd = "ssh -i {}".format(ssh_key) if ssh_key else "ssh"

    repo = Repo(repo_path)
    target_repo_ssh = extract_github_repo_ssh_url(target_repo)
    repo.remote().set_url(target_repo_ssh, push=True)
    log.debug("Push using ssh command: {}".format(git_ssh_cmd))
    branch = get_branch(task, "master")
    with repo.git.custom_environment(GIT_SSH_COMMAND=git_ssh_cmd):
        log.info("Pushing local changes to {}".format(target_repo_ssh))
        push_results = repo.remote().push(branch, verbose=True, set_upstream=True)

    try:
        _check_if_push_successful(push_results)
    except PushError:
        await strip_outgoing(config, task, repo_path)
        raise

    log.info("Push done succesfully!")


def _check_if_push_successful(push_results):
    if not push_results:
        raise PushError("GitPython failed to push but did not report any cause!")

    failures = []
    # XXX The only accepted flags are: PushInfo.FAST_FORWARD and PushInfo.UP_TO_DATE.
    # We may eventually want to add NEW_TAG the day treescript supports git tags.
    for flag_name, flag in (
        ("NEW_TAG", PushInfo.NEW_TAG),
        ("NEW_HEAD", PushInfo.NEW_HEAD),
        ("NO_MATCH", PushInfo.NO_MATCH),
        ("REJECTED", PushInfo.REJECTED),
        ("REMOTE_REJECTED", PushInfo.REMOTE_REJECTED),
        ("REMOTE_FAILURE", PushInfo.REMOTE_FAILURE),
        ("DELETED", PushInfo.DELETED),
        ("FORCED_UPDATE", PushInfo.FORCED_UPDATE),
        ("ERROR", PushInfo.ERROR),
    ):
        failures.extend([(result, flag_name) for result in push_results if result.flags & flag])

    if failures:
        raise PushError(
            "Some of the pushes had unexpected results: {}".format(
                ['Push "{}" reported "{}". '.format(result.summary, flag_name) for result, flag_name in failures]
            )
        )
