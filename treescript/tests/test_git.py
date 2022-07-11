import os
from contextlib import nullcontext as does_not_raise
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
from git import Actor, PushInfo
from scriptworker_client.utils import makedirs

from treescript import git
from treescript.exceptions import PushError
from treescript.script import get_default_config


@pytest.fixture(scope="function")
def task():
    return {"payload": {}, "metadata": {"source": "https://github.com/some-user/some-repo/blob/master/taskcluster/ci/version-bump"}}


@pytest.fixture(scope="function")
def config(tmpdir):
    config = get_default_config()
    config["work_dir"] = os.path.join(tmpdir, "work")
    config["artifact_dir"] = os.path.join(tmpdir, "artifact")
    makedirs(config["work_dir"])
    makedirs(config["artifact_dir"])
    config["git_ssh_config"] = {"default": {"emailAddress": "some-author@email.address"}}
    yield config


@pytest.mark.parametrize(
    "repo_subdir, branch, must_clone, must_checkout_branch",
    (
        (".", None, False, False),
        ("src", None, True, False),
        (".", "some-branch", False, True),
        ("src", "some-branch", True, True),
    ),
)
@pytest.mark.asyncio
async def test_checkout_repo(config, task, mocker, repo_subdir, branch, must_clone, must_checkout_branch):
    if branch:
        task["payload"]["branch"] = branch

    repo_mock = MagicMock()
    RepoClassMock = MagicMock()
    RepoClassMock.clone_from.return_value = repo_mock
    RepoClassMock.return_value = repo_mock
    mocker.patch.object(git, "Repo", RepoClassMock)

    @dataclass
    class _FetchInfo:
        name: str

    repo_mock.remotes.origin.fetch.return_value = [_FetchInfo("origin/master"), _FetchInfo("origin/some-branch")]

    master_branch = MagicMock()
    production_branch = MagicMock()
    repo_mock.branches = {"master": master_branch, "some-branch": production_branch}

    repo_path = os.path.join(config["work_dir"], repo_subdir)

    await git.checkout_repo(config, task, repo_path)

    if must_clone:
        RepoClassMock.clone_from.assert_called_once_with("https://github.com/some-user/some-repo", repo_path)
    else:
        RepoClassMock.assert_called_once_with(repo_path)

    if must_checkout_branch:
        repo_mock.create_head.assert_called_once_with(branch, "origin/some-branch")
        production_branch.checkout.assert_called_once_with()
    else:
        repo_mock.create_head.assert_not_called()
        production_branch.checkout.assert_not_called()


@pytest.mark.asyncio
async def test_get_existing_tags():
    with pytest.raises(NotImplementedError):
        await git.get_existing_tags({}, "")


@pytest.mark.asyncio
async def test_check_tags():
    with pytest.raises(NotImplementedError):
        await git.check_tags({}, "", "")


@pytest.mark.asyncio
async def test_get_revision():
    with pytest.raises(NotImplementedError):
        await git.get_revision({}, "", "")


@pytest.mark.asyncio
async def test_do_tagging():
    with pytest.raises(NotImplementedError):
        await git.check_tags({}, {}, "")


@pytest.mark.parametrize("output", ("git output!", None))
@pytest.mark.asyncio
async def test_log_outgoing(config, task, mocker, output):
    repo_mock = MagicMock()
    RepoClassMock = MagicMock()
    RepoClassMock.return_value = repo_mock
    mocker.patch.object(git, "Repo", RepoClassMock)
    repo_mock.git.diff.return_value = output
    repo_mock.iter_commits.return_value = ["some-commit", "another-commit"]

    number_of_changesets = await git.log_outgoing(config, task, config["work_dir"])

    assert number_of_changesets == 2
    repo_mock.iter_commits.assert_called_once_with("origin/master..master")
    repo_mock.git.diff.assert_called_once_with("origin/master")
    if output:
        with open(os.path.join(config["artifact_dir"], "public", "logs", "outgoing.diff"), "r") as fh:
            assert fh.read().rstrip() == output


@pytest.mark.asyncio
async def test_strip_outgoing(config, task, mocker):
    repo_mock = MagicMock()
    RepoClassMock = MagicMock()
    RepoClassMock.return_value = repo_mock
    mocker.patch.object(git, "Repo", RepoClassMock)

    await git.strip_outgoing(config, task, config["work_dir"])
    repo_mock.head.reset.assert_called_once_with(commit="origin/master", working_tree=True)
    repo_mock.git.clean.assert_called_once_with("-fdx")


@pytest.mark.asyncio
async def test_commit(config, task, mocker):
    repo_mock = MagicMock()
    RepoClassMock = MagicMock()
    RepoClassMock.return_value = repo_mock
    mocker.patch.object(git, "Repo", RepoClassMock)

    await git.commit(config, config["work_dir"], "some commit message")
    RepoClassMock.assert_called_once_with(config["work_dir"])
    repo_mock.git.add.assert_called_once_with(all=True)
    repo_mock.index.commit.assert_called_once_with(
        "some commit message",
        author=Actor("Mozilla Releng Treescript", "some-author@email.address"),
        committer=Actor("Mozilla Releng Treescript", "some-author@email.address"),
    )


@dataclass
class _PushInfo:
    flags: int
    summary: str = "somecommit..someothercommit"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ssh_key_file, push_return, expectation, expected_ssh_command",
    (
        ("some-file", [_PushInfo(PushInfo.FAST_FORWARD)], does_not_raise(), "ssh -i some-file"),
        (None, [_PushInfo(PushInfo.FAST_FORWARD)], does_not_raise(), "ssh"),
        (None, [], pytest.raises(PushError), None),
        (None, [_PushInfo(PushInfo.ERROR)], pytest.raises(PushError), None),
    ),
)
async def test_push(config, task, mocker, tmpdir, ssh_key_file, push_return, expectation, expected_ssh_command):
    repo_mock = MagicMock()
    RepoClassMock = MagicMock()
    RepoClassMock.return_value = repo_mock
    mocker.patch.object(git, "Repo", RepoClassMock)

    remote_mock = MagicMock()
    repo_mock.remote.return_value = remote_mock
    remote_mock.push.return_value = push_return

    config.setdefault("git_ssh_config", {}).setdefault("default", {})["keyfile"] = ssh_key_file

    with expectation:
        await git.push(config, task, tmpdir, "https://github.com/some-user/some-repo")
        remote_mock.set_url.assert_called_once_with("git@github.com:some-user/some-repo.git", push=True)
        remote_mock.push.assert_called_once_with("master", verbose=True, set_upstream=True)
        repo_mock.git.custom_environment.assert_called_once_with(GIT_SSH_COMMAND=expected_ssh_command)


@pytest.mark.parametrize(
    "push_results, expectation",
    (
        (
            [_PushInfo(PushInfo.FAST_FORWARD)],
            does_not_raise(),
        ),
        (
            [_PushInfo(PushInfo.UP_TO_DATE)],
            does_not_raise(),
        ),
        (
            [],
            pytest.raises(PushError),
        ),
        (
            [_PushInfo(PushInfo.NEW_TAG)],
            pytest.raises(PushError),
        ),
        (
            [_PushInfo(PushInfo.NEW_HEAD)],
            pytest.raises(PushError),
        ),
        (
            [_PushInfo(PushInfo.NO_MATCH)],
            pytest.raises(PushError),
        ),
        (
            [_PushInfo(PushInfo.REJECTED)],
            pytest.raises(PushError),
        ),
        (
            [_PushInfo(PushInfo.REMOTE_FAILURE)],
            pytest.raises(PushError),
        ),
        (
            [_PushInfo(PushInfo.DELETED)],
            pytest.raises(PushError),
        ),
        (
            [_PushInfo(PushInfo.FORCED_UPDATE)],
            pytest.raises(PushError),
        ),
        (
            [_PushInfo(PushInfo.ERROR)],
            pytest.raises(PushError),
        ),
    ),
)
def test_check_if_push_successful(push_results, expectation):
    with expectation:
        git._check_if_push_successful(push_results)
