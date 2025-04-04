import os
from contextlib import contextmanager

import pytest
from mozilla_version.gecko import FirefoxVersion, GeckoVersion, ThunderbirdVersion
from mozilla_version.mobile import MobileVersion

import treescript.gecko.versionmanip as vmanip
from treescript.exceptions import TaskVerificationError, TreeScriptError
from treescript.script import get_default_config
from treescript.util.task import DONTBUILD_MSG

try:
    from unittest.mock import AsyncMock
except ImportError:
    # TODO: Remove this import once py3.7 is not supported anymore
    from mock import AsyncMock


def is_slice_in_list(myslice, mylist):
    # Credit to https://stackoverflow.com/a/20789412/#answer-20789669
    # With edits by Callek to be py3 and pep8 compat
    len_s = len(myslice)  # so we don't recompute length of s on every iteration
    return any(myslice == mylist[i : len_s + i] for i in range(len(mylist) - len_s + 1))


@contextmanager
def does_not_raise():
    yield


@pytest.fixture(scope="function")
def config(tmpdir):
    config_ = get_default_config()
    config_["work_dir"] = os.path.join(tmpdir, "work")
    yield config_


@pytest.fixture(scope="function", params=("52.5.0", "52.0b3", "# foobar\n52.0a1", "60.1.3"))
def repo_context(tmpdir, config, request, mocker):
    context = mocker.MagicMock()
    context.repo = os.path.join(tmpdir, "repo")
    context.task = {"metadata": {"source": "https://hg.mozilla.org/repo/file/foo"}}
    context.config = config
    context.xtest_version = request.param
    if "\n" in request.param:
        context.xtest_version = [line for line in request.param.splitlines() if not line.startswith("#")][0]
    os.mkdir(context.repo)
    os.mkdir(os.path.join(context.repo, "config"))
    os.makedirs(os.path.join(context.repo, "browser", "config"))
    version_file = os.path.join(context.repo, "config", "milestone.txt")
    with open(version_file, "w") as f:
        f.write(request.param)
    display_version_file = os.path.join("browser", "config", "version.txt")
    with open(os.path.join(context.repo, display_version_file), "w") as f:
        f.write(context.xtest_version)
    display_version_file = os.path.join("browser", "config", "version_display.txt")
    with open(os.path.join(context.repo, display_version_file), "w") as f:
        f.write(context.xtest_version)
    yield context


def test_get_version(repo_context):
    ver = vmanip.get_version("config/milestone.txt", repo_context.repo, "https://hg.mozilla.org/repo")
    assert ver == repo_context.xtest_version


@pytest.mark.parametrize("new_version", ("68.0", "68.0b3"))
def test_replace_ver_in_file(repo_context, new_version):
    filepath = "config/milestone.txt"
    old_ver = repo_context.xtest_version
    vmanip.replace_ver_in_file(os.path.join(repo_context.repo, filepath), old_ver, new_version)
    assert new_version == vmanip.get_version(filepath, repo_context.repo, "https://hg.mozilla.org/repo")


@pytest.mark.parametrize("new_version", ("68.0", "68.0b3"))
def test_replace_ver_in_file_invalid_old_ver(repo_context, new_version):
    filepath = os.path.join(repo_context.repo, "config", "milestone.txt")
    old_ver = "45.0"
    with pytest.raises(Exception):
        vmanip.replace_ver_in_file(filepath, old_ver, new_version)


@pytest.mark.parametrize(
    "file, source_repo, expectation, expected_result",
    (
        ("browser/config/version.txt", "https://hg.mozilla.org/mozilla-central", does_not_raise(), FirefoxVersion),
        ("browser/config/version_display.txt", "https://hg.mozilla.org/releases/mozilla-beta", does_not_raise(), FirefoxVersion),
        ("mail/config/version.txt", "https://hg.mozilla.org/releases/comm-beta", does_not_raise(), ThunderbirdVersion),
        ("mail/config/version_display.txt", "https://hg.mozilla.org/releases/comm-release", does_not_raise(), ThunderbirdVersion),
        ("config/milestone.txt", "https://hg.mozilla.org/releases/mozilla-release", does_not_raise(), GeckoVersion),
        ("some/random/file.txt", "https://hg.mozilla.org/mozilla-central", pytest.raises(TreeScriptError), None),
        ("some/random/file.txt", "https://github.com/some-owner/some-repo", pytest.raises(TreeScriptError), None),
        ("mobile/android/version.txt", "https://hg.mozilla.org/mozilla-central", does_not_raise(), MobileVersion),
    ),
)
def test_find_what_version_parser_to_use(file, source_repo, expectation, expected_result):
    with expectation:
        assert vmanip._find_what_version_parser_to_use(file, source_repo) == expected_result


@pytest.mark.asyncio
@pytest.mark.parametrize("new_version", ("68.0", "68.0b3"))
async def test_bump_version_DONTBUILD_true(mocker, repo_context, new_version):
    relative_files = [os.path.join("config", "milestone.txt")]
    bump_info = {"files": relative_files, "next_version": new_version}
    mocked_bump_info = mocker.patch.object(vmanip, "get_version_bump_info")
    mocked_bump_info.return_value = bump_info
    mocked_dontbuild = mocker.patch.object(vmanip, "get_dontbuild")
    mocked_dontbuild.return_value = True
    vcs_mock = AsyncMock()
    mocker.patch.object(vmanip, "vcs", new=vcs_mock)
    await vmanip.bump_version(repo_context.config, repo_context.task, repo_context.repo)
    commit_msg = vcs_mock.commit.call_args_list[0][0][2]
    assert DONTBUILD_MSG in commit_msg


@pytest.mark.asyncio
@pytest.mark.parametrize("new_version", ("68.0", "68.0b3"))
async def test_bump_version_DONTBUILD_false(mocker, repo_context, new_version):
    relative_files = [os.path.join("config", "milestone.txt")]
    bump_info = {"files": relative_files, "next_version": new_version}
    mocked_bump_info = mocker.patch.object(vmanip, "get_version_bump_info")
    mocked_bump_info.return_value = bump_info
    mocked_dontbuild = mocker.patch.object(vmanip, "get_dontbuild")
    mocked_dontbuild.return_value = False
    vcs_mock = AsyncMock()
    mocker.patch.object(vmanip, "vcs", new=vcs_mock)
    await vmanip.bump_version(repo_context.config, repo_context.task, repo_context.repo)
    commit_msg = vcs_mock.commit.call_args_list[0][0][2]
    assert DONTBUILD_MSG not in commit_msg


@pytest.mark.asyncio
@pytest.mark.parametrize("new_version", ("68.0", "68.0b3", "68.9.10esr"))
async def test_bump_version_invalid_file(mocker, repo_context, new_version):
    relative_files = [os.path.join("config", "invalid_file.txt"), os.path.join("config", "milestone.txt")]
    bump_info = {"files": relative_files, "next_version": new_version}
    mocked_bump_info = mocker.patch.object(vmanip, "get_version_bump_info")
    mocked_bump_info.return_value = bump_info
    vcs_mock = AsyncMock()
    mocker.patch.object(vmanip, "vcs", new=vcs_mock)
    with pytest.raises(TaskVerificationError):
        await vmanip.bump_version(repo_context.config, repo_context.task, repo_context.repo)
    assert repo_context.xtest_version == vmanip.get_version(relative_files[1], repo_context.repo, "https://hg.mozilla.org/repo")
    vcs_mock.commit.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("new_version", ("68.0", "68.0b3", "68.9.10esr"))
async def test_bump_version_missing_file(mocker, repo_context, new_version):
    # Test only creates config/milestone.txt
    remove_file = os.path.join(repo_context.repo, "browser", "config", "version_display.txt")
    os.remove(remove_file)

    relative_files = [os.path.join("browser", "config", "version_display.txt"), os.path.join("config", "milestone.txt")]
    bump_info = {"files": relative_files, "next_version": new_version}
    mocked_bump_info = mocker.patch.object(vmanip, "get_version_bump_info")
    mocked_bump_info.return_value = bump_info
    vcs_mock = AsyncMock()
    mocker.patch.object(vmanip, "vcs", new=vcs_mock)
    with pytest.raises(TaskVerificationError):
        await vmanip.bump_version(repo_context.config, repo_context.task, repo_context.repo)
    assert repo_context.xtest_version == vmanip.get_version(relative_files[1], repo_context.repo, "https://hg.mozilla.org/repo")
    vcs_mock.commit.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("new_version", ("24.0", "31.0b3", "45.0esr"))
async def test_bump_version_smaller_version(mocker, repo_context, new_version):
    relative_files = [os.path.join("config", "milestone.txt")]
    bump_info = {"files": relative_files, "next_version": new_version}
    mocked_bump_info = mocker.patch.object(vmanip, "get_version_bump_info")
    mocked_bump_info.return_value = bump_info
    vcs_mock = AsyncMock()
    mocker.patch.object(vmanip, "vcs", new=vcs_mock)
    await vmanip.bump_version(repo_context.config, repo_context.task, repo_context.repo)
    assert repo_context.xtest_version == vmanip.get_version(relative_files[0], repo_context.repo, "https://hg.mozilla.org/repo")
    vcs_mock.commit.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("new_version,expect_version", (("60.2.0esr", "60.2.0"), ("68.0.1esr", "68.0.1"), ("68.9.10esr", "68.9.10")))
async def test_bump_version_esr(mocker, repo_context, new_version, expect_version):
    if not repo_context.xtest_version.endswith("esr"):
        # XXX pytest.skip raised exceptions here because betas don't turn into esrs
        return

    relative_files = [os.path.join("config", "milestone.txt")]
    bump_info = {"files": relative_files, "next_version": new_version}
    mocked_bump_info = mocker.patch.object(vmanip, "get_version_bump_info")
    mocked_bump_info.return_value = bump_info
    vcs_mock = AsyncMock()
    mocker.patch.object(vmanip, "vcs", new=vcs_mock)
    display_version_file = os.path.join("browser", "config", "version_display.txt")
    with open(os.path.join(repo_context.repo, display_version_file), "r+") as f:
        f.seek(0, os.SEEK_END)
        f.write("esr")

    await vmanip.bump_version(repo_context.config, repo_context.task, repo_context.repo)
    assert expect_version == vmanip.get_version(relative_files[0], repo_context.repo, "https://hg.mozilla.org/repo")
    assert expect_version == vmanip.get_version(relative_files[1], repo_context.repo, "https://hg.mozilla.org/repo")
    assert new_version == vmanip.get_version(relative_files[2], repo_context.repo, "https://hg.mozilla.org/repo")
    vcs_mock.commit.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("new_version", ("60.0", "68.0.1"))
async def test_bump_version_non_esr(mocker, config, tmpdir, new_version):
    version = "52.0.1"
    repo = os.path.join(tmpdir, "repo")
    os.mkdir(repo)
    os.mkdir(os.path.join(repo, "config"))
    os.makedirs(os.path.join(repo, "browser", "config"))
    version_file = os.path.join("config", "milestone.txt")
    with open(os.path.join(repo, version_file), "w") as f:
        f.write(version)
    display_version_file = os.path.join("browser", "config", "version_display.txt")
    with open(os.path.join(repo, display_version_file), "w") as f:
        f.write(version)

    relative_files = [os.path.join("browser", "config", "version_display.txt"), os.path.join("config", "milestone.txt")]
    bump_info = {"files": relative_files, "next_version": new_version}
    mocked_bump_info = mocker.patch.object(vmanip, "get_version_bump_info")
    mocked_bump_info.return_value = bump_info
    task = {
        "metadata": {
            "source": "https://hg.mozilla.org/repo/file/deadb33f/.taskcluster.yml",
        },
    }
    vcs_mock = AsyncMock()
    mocker.patch.object(vmanip, "vcs", new=vcs_mock)
    await vmanip.bump_version(config, task, repo)
    assert new_version == vmanip.get_version(display_version_file, repo, "https://hg.mozilla.org/repo")
    assert new_version == vmanip.get_version(version_file, repo, "https://hg.mozilla.org/repo")
    vcs_mock.commit.assert_called_once()


@pytest.mark.asyncio
async def test_bump_version_same_version(mocker, repo_context):
    relative_files = [os.path.join("config", "milestone.txt")]
    bump_info = {"files": relative_files, "next_version": repo_context.xtest_version}
    mocked_bump_info = mocker.patch.object(vmanip, "get_version_bump_info")
    mocked_bump_info.return_value = bump_info
    vcs_mock = AsyncMock()
    mocker.patch.object(vmanip, "vcs", new=vcs_mock)
    await vmanip.bump_version(repo_context.config, repo_context.task, repo_context.repo)
    assert repo_context.xtest_version == vmanip.get_version(relative_files[0], repo_context.repo, "https://hg.mozilla.org/repo")
    vcs_mock.commit.assert_not_called()
