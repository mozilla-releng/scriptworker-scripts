import os
import shutil
from contextlib import contextmanager

import hglib
import pytest
from mozilla_version.gecko import FirefoxVersion

import treescript.merges as merges
from treescript.exceptions import TaskVerificationError
from treescript.script import get_default_config


@contextmanager
def does_not_raise():
    yield


@pytest.fixture(scope="function")
def task():
    return {"payload": {}, "metadata": {"source": "https://hg.mozilla.org/repo-name/file/filename"}}


@pytest.fixture(scope="function")
def merge_info():
    return {
        "version_files": [{"filename": "browser/config/version.txt"}, {"filename": "config/milestone.txt"}],
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


@pytest.fixture(scope="function")
def merge_bump_info():
    return {
        "version_files": [],
        "version_files_suffix": ["browser/config/version_display.txt", "browser/config/version.txt", "config/milestone.txt"],
        "version_suffix": "a1",
        "copy_files": [],
        "replacements": [],
        "to_branch": "central",
        "to_repo": "https://hg.mozilla.org/mozilla-central",
        "merge_old_head": False,
        "end_tag": "FIREFOX_NIGHTLY_{major_version}_END",
    }


@pytest.fixture(scope="function")
def config(tmpdir):
    config_ = get_default_config()
    config_["work_dir"] = os.path.join(tmpdir, "work")
    config_["artifact_dir"] = os.path.join(tmpdir, "artifacts")
    config_["hg_ssh_user"] = "sshuser"
    config_["merge_day_clobber_file"] = "CLOBBER"
    config_["upstream_repo"] = "https://hg.mozilla.org/repo/fake_upstream"
    yield config_


@pytest.fixture(scope="function")
def repo_context(tmpdir, config, request, mocker):
    context = mocker.MagicMock()
    context.repo = os.path.join(tmpdir, "repo")
    context.task = {"metadata": {"source": "https://hg.mozilla.org/repo/file/foo"}}
    context.config = config
    hglib.init(context.repo)
    os.mkdir(os.path.join(context.repo, "config"))
    replacement_file = os.path.join(context.repo, "config", "replaceme.txt")
    with open(replacement_file, "w") as f:
        f.write("dummytext")
    clobber_file = os.path.join(context.repo, config["merge_day_clobber_file"])
    with open(clobber_file, "w") as f:
        f.write("# A comment\n\nthiswillgetremoved")

    for platform in ("linux32", "linux64"):
        mozconfig = os.path.join(context.repo, "browser/config/mozconfigs", platform, "l10n-mozconfig")
        os.makedirs(os.path.dirname(mozconfig), exist_ok=True)
        with open(mozconfig, "w") as f:
            f.write("ac_add_options --with-branding=browser/branding/nightly\n")

    version_file = os.path.join(context.repo, "browser/config/version.txt")
    milestone_file = os.path.join(context.repo, "config/milestone.txt")
    with open(version_file, "w") as f:
        f.write("51.0")
    with open(milestone_file, "w") as f:
        f.write("51.0a1")
    with hglib.open(context.repo) as repo:
        repo.addremove()
        repo.commit("init")
        repo.tag([b"old_central"], message="first tag to make sure .hgtags exists")
        with open(milestone_file, "w") as f:
            f.write("51.0")
        repo.commit("51 becomes beta")
        repo.tag([b"old_beta"], message="51 beta tag")
        repo.bookmark(b"beta", inactive=True)
        repo.update(b".^")
    with open(version_file, "w") as f:
        f.write("52.0")
    with open(milestone_file, "w") as f:
        f.write("52.0a1")
    with hglib.open(context.repo) as repo:
        repo.commit("version bump")
        repo.bookmark(b"central", inactive=True)
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


@pytest.mark.parametrize(
    "config_no_clobber,break_things,expectation",
    (
        (False, False, does_not_raise()),
        (False, True, pytest.raises(FileNotFoundError)),
        # Test case for a repo that does not have a CLOBBER file
        (True, False, does_not_raise()),
    ),
)
def test_touch_clobber_file(repo_context, config_no_clobber, break_things, expectation):
    if config_no_clobber:
        repo_context.config["merge_day_clobber_file"] = ""
        os.unlink(os.path.join(repo_context.repo, "CLOBBER"))
        clobber_file = None
    else:
        clobber_file = os.path.join(repo_context.repo, repo_context.config["merge_day_clobber_file"])

        if break_things:
            os.unlink(clobber_file)

    with expectation:
        merges.touch_clobber_file(repo_context.config, repo_context.repo)

        if clobber_file:
            with open(clobber_file) as f:
                contents = f.read()
                assert "Merge day clobber" in contents


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "merge_config,expected",
    (
        ({"version_files": [{"filename": "config/milestone.txt", "new_suffix": ""}]}, [["config/milestone.txt"]]),
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
        called_args.extend(arguments)

    def noop_copyfile(*arguments, **kwargs):
        called_args.append("shutil.copyfile")

    def noop_replace(*arguments, **kwargs):
        called_args.append("replace")

    def mocked_get_version(path, repo_path):
        return FirefoxVersion.parse("76.0")

    mocker.patch.object(merges, "get_version", new=mocked_get_version)
    mocker.patch.object(merges, "do_bump_version", new=noop_bump_version)
    mocker.patch.object(shutil, "copyfile", new=noop_copyfile)
    mocker.patch.object(merges, "replace", new=noop_replace)
    mocker.patch.object(merges, "touch_clobber_file", new=sync_noop)

    await merges.apply_rebranding(config, repo_context.repo, merge_config)
    assert called_args[0] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "version_config,current_version, expected",
    (
        # central-to-beta
        ({"filename": "config/milestone.txt", "new_suffix": ""}, FirefoxVersion.parse("75.0a1"), "75.0"),
        ({"filename": "browser/config/version_display.txt", "new_suffix": "b1"}, FirefoxVersion.parse("75.0a1"), "75.0b1"),
        # beta-to-release
        ({"filename": "browser/config/version_display.txt", "new_suffix": ""}, FirefoxVersion.parse("75.0b9"), "75.0"),
        # bump_central
        ({"filename": "config/milestone.txt", "version_bump": "major"}, FirefoxVersion.parse("75.0a1"), "76.0a1"),
        ({"filename": "config/milestone.txt", "version_bump": "major"}, FirefoxVersion.parse("75.0"), "76.0"),
        # bump_esr
        ({"filename": "browser/config/version.txt", "version_bump": "minor"}, FirefoxVersion.parse("68.1.0"), "68.2.0"),
        ({"filename": "browser/config/version_display.txt", "version_bump": "minor"}, FirefoxVersion.parse("68.1.0esr"), "68.2.0esr"),
    ),
)
async def test_create_new_version(config, mocker, version_config, current_version, expected):
    def mocked_get_version(path, repo_path):
        return current_version

    mocker.patch.object(merges, "get_version", new=mocked_get_version)

    result = merges.create_new_version(version_config, repo_path="")  # Dummy repo_path, ignored.
    assert result == expected


def set_up_merge_mocks(mocker, called_args):
    orig_run_hg_command = merges.run_hg_command

    async def mocked_run_hg_command(config, *arguments, repo_path=None, **kwargs):
        called_args.append([arguments])
        if arguments[0] == "pull":
            return
        return await orig_run_hg_command(config, *arguments, repo_path=repo_path, **kwargs)

    async def noop_l10n_bump(*arguments, **kwargs):
        called_args.append("l10n_bump")

    orig_commit = merges.commit

    async def mocked_commit(*arguments, **kwargs):
        called_args.append("commit")
        return await orig_commit(*arguments, **kwargs)

    orig_apply_rebranding = merges.apply_rebranding

    async def mocked_apply_rebranding(*arguments, **kwargs):
        called_args.append("apply_rebranding")
        return await orig_apply_rebranding(*arguments, **kwargs)

    mocker.patch.object(merges, "run_hg_command", new=mocked_run_hg_command)
    mocker.patch.object(merges, "commit", new=mocked_commit)
    mocker.patch.object(merges, "apply_rebranding", new=mocked_apply_rebranding)
    mocker.patch.object(merges, "l10n_bump", new=noop_l10n_bump)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "add_merge_info,raises,expected_calls,l10n_bump,expected_return",
    (
        (
            True,
            does_not_raise(),
            14,
            False,
            [("https://hg.mozilla.org/mozilla-central", "some_revision"), ("https://hg.mozilla.org/releases/mozilla-beta", "some_revision")],
        ),
        (
            True,
            does_not_raise(),
            16,
            True,
            [("https://hg.mozilla.org/mozilla-central", "some_revision"), ("https://hg.mozilla.org/releases/mozilla-beta", "some_revision")],
        ),
        (False, pytest.raises(TaskVerificationError), 0, False, None),
    ),
)
async def test_do_merge(mocker, config, task, repo_context, merge_info, add_merge_info, raises, expected_calls, l10n_bump, expected_return):

    called_args = []
    if add_merge_info:
        task["payload"]["merge_info"] = merge_info
    if l10n_bump:
        task["payload"]["l10n_bump_info"] = {"foo": "bar"}
    set_up_merge_mocks(mocker, called_args)

    result = None
    with raises:
        result = await merges.do_merge(config, task, repo_context.repo)

    assert len(called_args) == expected_calls
    if result is not None:
        # update bookmarks so the second merge attempts knows where to start
        with hglib.open(repo_context.repo) as repo:
            repo.bookmark(b"central", result[0][1].encode("ascii"), inactive=True)
            repo.bookmark(b"beta", result[1][1].encode("ascii"), inactive=True)
        # replace commit ids in result with dummy string
        result = [(tree, "some_revision") for (tree, rev) in result]
    assert result == expected_return

    # try again, to ensure do_merge is idempotent
    try:
        result = await merges.do_merge(config, task, repo_context.repo)
    except Exception:
        pass
    assert not result


@pytest.mark.asyncio
async def test_bump_central(mocker, config, task, repo_context, merge_bump_info):
    task["payload"]["merge_info"] = merge_bump_info
    called_args = []

    async def mocked_run_hg_command(config, *arguments, repo_path=None, **kwargs):
        called_args.append(arguments)
        if "return_output" in kwargs:
            return "headers\n\n\n\n+invalid_changeset tag\n changeset tag\n+valid_changeset_is_forty_characters_long tag"

    async def mocked_commit(config, repo_path, commit_msg, **kwargs):
        called_args.append(("commit", commit_msg))

    async def mocked_get_revision(*args, **kwargs):
        return "some_revision"

    async def noop_apply_rebranding(*arguments, **kwargs):
        called_args.append(("apply_rebranding"))

    mocker.patch.object(merges, "run_hg_command", new=mocked_run_hg_command)
    mocker.patch.object(merges, "commit", new=mocked_commit)
    mocker.patch.object(merges, "get_revision", new=mocked_get_revision)
    mocker.patch.object(merges, "apply_rebranding", new=noop_apply_rebranding)

    result = await merges.do_merge(config, task, repo_context.repo)

    expected_calls = [
        ("pull", "https://hg.mozilla.org/repo/fake_upstream"),
        ("up", "-C", "central"),
        (
            "tag",
            "-m",
            "No bug - tagging some_revision with FIREFOX_NIGHTLY_52_END a=release DONTBUILD CLOSED TREE",
            "-r",
            "some_revision",
            "-f",
            "FIREFOX_NIGHTLY_52_END",
        ),
        ("diff",),
        ("apply_rebranding"),
        ("commit", "Update configs. IGNORE BROKEN CHANGESETS CLOSED TREE NO BUG a=release ba=release"),
    ]
    for expected in expected_calls:
        assert expected in called_args
    assert result == [("https://hg.mozilla.org/mozilla-central", "some_revision")]


@pytest.mark.parametrize(
    "merge_config,expected", (({}, "browser/config/version.txt"), ({"fetch_version_from": "some/other/version.txt"}, "some/other/version.txt"))
)
def test_core_version_file(merge_config, expected):
    assert merges.core_version_file(merge_config) == expected


def test_formatter():
    fmt = merges.BashFormatter()
    assert fmt.format("Foo ${bar} {baz}", baz="BAZ") == "Foo ${bar} BAZ"
    assert fmt.format("Foo ${bar} {}", "BAZ") == "Foo ${bar} BAZ"
