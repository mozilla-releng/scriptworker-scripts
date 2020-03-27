import os
import shutil
from contextlib import contextmanager

import pytest

import treescript.merges as merges
from treescript.exceptions import TaskVerificationError
from treescript.script import get_default_config


@contextmanager
def does_not_raise():
    yield


@pytest.yield_fixture(scope="function")
def task():
    return {"payload": {}, "metadata": {"source": "https://hg.mozilla.org/repo-name/file/filename"}}


@pytest.yield_fixture(scope="function")
def merge_info():
    return {
        "version_files": ["browser/config/version.txt", "config/milestone.txt"],
        "version_files_suffix": ["browser/config/version_display.txt"],
        "version_suffix": "b1",
        "copy_files": [["browser/config/version.txt", "browser/config/version_display.txt"]],
        "replacements": [
            [
                "browser/config/mozconfigs/linux32/l10n-mozconfig",
                "ac_add_options --with-branding=browser/branding/nightly",
                "ac_add_options --enable-official-branding",
            ],
            [
                "browser/config/mozconfigs/linux64/l10n-mozconfig",
                "ac_add_options --with-branding=browser/branding/nightly",
                "ac_add_options --enable-official-branding",
            ],
        ],
        "from_branch": "central",
        "to_branch": "beta",
        "from_repo": "https://hg.mozilla.org/mozilla-central",
        "to_repo": "https://hg.mozilla.org/releases/mozilla-beta",
        "merge_old_head": True,
        "base_tag": "FIREFOX_BETA_{major_version}_BASE",
        "end_tag": "FIREFOX_BETA_{major_version}_END",
    }


@pytest.yield_fixture(scope="function")
def config(tmpdir):
    config_ = get_default_config()
    config_["work_dir"] = os.path.join(tmpdir, "work")
    config_["artifact_dir"] = os.path.join(tmpdir, "artifacts")
    config_["hg_ssh_user"] = "sshuser"
    yield config_


@pytest.fixture(scope="function")
def repo_context(tmpdir, config, request, mocker):
    context = mocker.MagicMock()
    context.repo = os.path.join(tmpdir, "repo")
    context.task = {"metadata": {"source": "https://hg.mozilla.org/repo/file/foo"}}
    context.config = config
    os.mkdir(context.repo)
    os.mkdir(os.path.join(context.repo, "config"))
    replacement_file = os.path.join(context.repo, "config", "replaceme.txt")
    with open(replacement_file, "w") as f:
        f.write("dummytext")
    clobber_file = os.path.join(context.repo, "CLOBBER")
    with open(clobber_file, "w") as f:
        f.write("# A comment\n\nthiswillgetremoved")

    version_file = os.path.join(context.repo, "browser/config/version.txt")
    os.makedirs(os.path.dirname(version_file))
    with open(version_file, "w") as f:
        f.write("52.0")
    yield context


@pytest.mark.parametrize(
    "expectation,filename,from_,to_",
    (
        (does_not_raise(), "config/replaceme.txt", "dummytext", "alsodummytext"),
        (pytest.raises(ValueError), "config/replaceme.txt", "textnotfound", "alsodummytext"),
        (pytest.raises(FileNotFoundError), "config/doesnotexist", "dummytext", "52.5.0"),
    ),
)
def test_replace(repo_context, expectation, filename, from_, to_):
    file_path = os.path.join(repo_context.repo, filename)
    with expectation:
        merges.replace(file_path, from_, to_)
        with open(file_path) as f:
            assert f.read() == to_


@pytest.mark.parametrize("break_things,expectation", ((False, does_not_raise()), (True, pytest.raises(FileNotFoundError))))
def test_touch_clobber_file(repo_context, break_things, expectation):
    clobber_file = os.path.join(repo_context.repo, "CLOBBER")

    if break_things:
        os.unlink(clobber_file)

    with expectation:
        merges.touch_clobber_file(repo_context.repo)

        with open(clobber_file) as f:
            contents = f.read()
            assert "Merge day clobber" in contents


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "merge_config,expected",
    (
        ({"version_files": ["browser/config/version.txt"]}, [["browser/config/version.txt"]]),
        ({"version_files_suffix": ["browser/config/version_display.txt"]}, [["browser/config/version_display.txt"]]),
        ({"copy_files": [["browser/config/version.txt", "browser/config/version_display.txt"]]}, "shutil.copyfile"),
        (
            {"replacements": [("build/mozconfig.common", "MOZ_REQUIRE_SIGNING=${MOZ_REQUIRE_SIGNING-0}", "MOZ_REQUIRE_SIGNING=${MOZ_REQUIRE_SIGNING-1}")]},
            "replace",
        ),
    ),
)
async def test_apply_rebranding(config, repo_context, mocker, merge_config, expected):
    # Can't easily check the arguments here because they're full paths to tmpdirs.
    called_args = []

    async def noop_bump_version(*arguments, **kwargs):
        called_args.append([arguments[2]])

    def sync_noop(*arguments, **kwargs):
        called_args.append(*arguments)

    def noop_copyfile(*arguments, **kwargs):
        called_args.append("shutil.copyfile")

    def noop_replace(*arguments, **kwargs):
        called_args.append("replace")

    mocker.patch.object(merges, "do_bump_version", new=noop_bump_version)
    mocker.patch.object(shutil, "copyfile", new=noop_copyfile)
    mocker.patch.object(merges, "replace", new=noop_replace)
    mocker.patch.object(merges, "touch_clobber_file", new=sync_noop)

    await merges.apply_rebranding(config, repo_context.repo, merge_config)
    assert called_args[0] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "add_merge_info,raises,expected_calls,expected_return",
    (
        (
            True,
            does_not_raise(),
            13,
            [("https://hg.mozilla.org/mozilla-central", "some_revision"), ("https://hg.mozilla.org/releases/mozilla-beta", "some_revision")],
        ),
        (False, pytest.raises(TaskVerificationError), 0, None),
    ),
)
async def test_do_merge(mocker, config, task, repo_context, merge_info, add_merge_info, raises, expected_calls, expected_return):

    called_args = []
    if add_merge_info:
        task["payload"]["merge_info"] = merge_info

    async def mocked_run_hg_command(config, *arguments, repo_path=None, **kwargs):
        called_args.append([arguments])
        if "return_output" in kwargs:
            return "headers\n\n\n\n+invalid_changeset tag\n changeset tag\n+valid_changeset_is_forty_characters_long tag"

    async def mocked_get_revision(*args, **kwargs):
        return "some_revision"

    async def noop_apply_rebranding(*arguments, **kwargs):
        called_args.append("apply_rebranding")

    mocker.patch.object(merges, "run_hg_command", new=mocked_run_hg_command)
    mocker.patch.object(merges, "get_revision", new=mocked_get_revision)
    mocker.patch.object(merges, "apply_rebranding", new=noop_apply_rebranding)

    result = None
    with raises:
        result = await merges.do_merge(config, task, repo_context.repo)

    assert len(called_args) == expected_calls
    assert result == expected_return
