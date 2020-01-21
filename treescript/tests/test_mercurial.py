"""Tests for mercurial functionality.

We don't test the robustcheckout extension here, nor is this file about integration
testing with mercurial commands, we are testing that we can call mercurial and that
it's expected output is something our script can cope with.

"""

import os

import pytest

from scriptworker_client.utils import makedirs
from treescript import mercurial
from treescript.exceptions import FailedSubprocess, PushError
from treescript.script import get_default_config
from treescript.task import DONTBUILD_MSG

# constants, helpers, fixtures {{{1
ROBUSTCHECKOUT_FILES = (
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "build", "lib", "treescript", "py2", "robustcheckout.py")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "treescript", "py2", "robustcheckout.py")),
)
UNEXPECTED_ENV_KEYS = "HG HGPROF CDPATH GREP_OPTIONS http_proxy no_proxy " "HGPLAINEXCEPT EDITOR VISUAL PAGER NO_PROXY CHGDEBUG".split()


@pytest.yield_fixture(scope="function")
def task():
    return {"payload": {}, "metadata": {"source": "https://hg.mozilla.org/repo-name/file/filename"}}


async def noop_async(*args, **kwargs):
    pass


async def check_tags(_, tag_info, *args):
    return tag_info["tags"]


def is_slice_in_list(s, l):
    # Credit to https://stackoverflow.com/a/20789412/#answer-20789669
    # With edits by Callek to be py3 and pep8 compat
    len_s = len(s)  # so we don't recompute length of s on every iteration
    return any(s == l[i : len_s + i] for i in range(len(l) - len_s + 1))


@pytest.yield_fixture(scope="function")
def config(tmpdir):
    config = get_default_config()
    config["work_dir"] = os.path.join(tmpdir, "work")
    config["artifact_dir"] = os.path.join(tmpdir, "artifact")
    makedirs(config["work_dir"])
    makedirs(config["artifact_dir"])
    yield config


# build_hg_cmd {{{1
@pytest.mark.parametrize("hg,args", (("hg", ["blah", "blah", "--baz"]), (["hg"], ["blah", "blah", "--baz"])))
def test_build_hg_cmd(config, hg, args):
    config["hg"] = hg
    valid_paths = []
    # allow for different install types
    for path in ROBUSTCHECKOUT_FILES:
        valid_paths.append(
            [
                "hg",
                "--config",
                "extensions.robustcheckout={}".format(path),
                "--config",
                "extensions.purge=",
                "--config",
                "extensions.strip=",
                "blah",
                "blah",
                "--baz",
            ]
        )
    assert mercurial.build_hg_command(config, *args) in valid_paths


@pytest.mark.parametrize(
    "my_env",
    (
        {
            # Blank
        },
        {"HGPLAIN": "0", "LANG": "en_US.utf8"},  # defaults wrong
        {k: "whatever" for k in UNEXPECTED_ENV_KEYS},  # Values to strip from env
    ),
)
def test_build_hg_env(mocker, my_env):
    mocker.patch.dict(mercurial.os.environ, my_env)
    returned_env = mercurial.build_hg_environment()
    assert (set(UNEXPECTED_ENV_KEYS) & set(returned_env.keys())) == set()
    assert returned_env["HGPLAIN"] == "1"
    assert returned_env["LANG"] == "C"
    for key in returned_env.keys():
        assert type(returned_env[key]) == str


# run_hg_command {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize("args", (["foobar", "--bar"], ["--test", "args", "banana"]))
async def test_run_hg_command(mocker, config, args):
    called_args = []

    async def run_command(*arguments, **kwargs):
        called_args.append([*arguments, kwargs])

    mocker.patch.object(mercurial, "run_command", new=run_command)
    env_call = mocker.patch.object(mercurial, "build_hg_environment")
    cmd_call = mocker.patch.object(mercurial, "build_hg_command")
    env = {"HGPLAIN": 1, "LANG": "C"}
    env_call.return_value = env
    cmd_call.return_value = ["hg", *args]

    await mercurial.run_hg_command(config, *args)

    env_call.assert_called_with()
    cmd_call.assert_called_with(config, *args)
    assert called_args[0][0] == ["hg"] + args
    assert called_args[0][1]["env"] == env
    assert len(called_args) == 1


@pytest.mark.asyncio
async def test_run_hg_command_localrepo(mocker, config):
    args = ["foobar", "--bar"]
    called_args = []

    async def run_command(*arguments, **kwargs):
        called_args.append([*arguments, kwargs])

    mocker.patch.object(mercurial, "run_command", new=run_command)
    env_call = mocker.patch.object(mercurial, "build_hg_environment")
    cmd_call = mocker.patch.object(mercurial, "build_hg_command")
    env = {"HGPLAIN": 1, "LANG": "C"}
    env_call.return_value = env
    cmd_call.return_value = ["hg", *args]

    await mercurial.run_hg_command(config, *args, repo_path="/tmp/localrepo")

    env_call.assert_called_with()
    cmd_call.assert_called_with(config, *args)
    assert len(called_args) == 1
    is_slice_in_list(["-R", "/tmp/localrepo"], called_args[0][0])


# robustcheckout, hg {{{1
@pytest.mark.asyncio
async def test_hg_version(config, mocker):
    logged = []

    def info(msg, *args):
        logged.append(msg % args)

    mocklog = mocker.patch.object(mercurial, "log")
    mocklog.info = info
    await mercurial.log_mercurial_version(config)

    assert logged[0].startswith("Mercurial Distributed SCM (version")


@pytest.mark.asyncio
async def test_validate_robustcheckout_works(config, mocker):
    mocker.patch.object(mercurial, "run_hg_command", new=noop_async)
    ret = await mercurial.validate_robustcheckout_works(config)
    assert ret is True


@pytest.mark.asyncio
async def test_validate_robustcheckout_works_doesnt(config, mocker):
    mocked = mocker.patch.object(mercurial, "run_hg_command")
    mocked.side_effect = FailedSubprocess("Mocked failure in test harness")
    ret = await mercurial.validate_robustcheckout_works(config)
    assert ret is False


# checkout_repo {{{1
@pytest.mark.parametrize("branch", (None, "foo"))
@pytest.mark.asyncio
async def test_checkout_repo(config, task, mocker, branch):
    """checkout_repo calls the expected commands.
    """
    calls = [
        ("robustcheckout", "https://hg.mozilla.org/test-repo", os.path.join(config["work_dir"])),
        ("strip", "--no-backup", "outgoing()"),
        ("up", "-C"),
        ("purge", "--all"),
        ("pull", "-b"),
        ("update", "-r"),
    ]
    if branch:
        task["payload"]["branch"] = branch

    async def check_params(*args, **kwargs):
        assert is_slice_in_list(calls.pop(0), args)

    mocker.patch.object(mercurial, "run_hg_command", new=check_params)
    mocker.patch.object(mercurial, "get_source_repo").return_value = "https://hg.mozilla.org/test-repo"

    config["hg_share_base_dir"] = "/builds/hg-shared-test"
    config["upstream_repo"] = "https://hg.mozilla.org/mozilla-test-unified"

    await mercurial.checkout_repo(config, task, config["work_dir"])


# do_tagging {{{1
@pytest.mark.asyncio
async def test_get_existing_tags(config, mocker, tmpdir):
    """get_existing_tags returns a dictionary of tag:revision from
    ``hg tags --template=json`` output.

    """
    expected = {"tag1": "rev1", "tag2": "rev2"}

    async def fake_hg_command(*args, **kwargs):
        return """
        [{
            "node": "rev1",
            "rev": 1,
            "tag": "tag1",
            "type": ""
        }, {
            "node": "rev2",
            "rev": 2,
            "tag": "tag2",
            "type": ""
        }]
    """

    mocker.patch.object(mercurial, "run_hg_command", new=fake_hg_command)
    assert await mercurial.get_existing_tags(config, tmpdir) == expected


@pytest.mark.asyncio
async def test_check_tags(config, mocker, tmpdir):
    """check_tags drops duplicate tags, keeps missing tags, and also keeps
    duplicate tags that are on different revisions.

    """
    existing_tags = {"duplicate_tag": "my_revision", "duplicate_tag_different_revision": "different_revision", "extra_tag": "another_revision"}
    expected = ["duplicate_tag_different_revision", "new_tag"]
    tag_info = {"revision": "my_revision", "tags": ["duplicate_tag", "duplicate_tag_different_revision", "new_tag"]}

    async def get_existing_tags(*args):
        return existing_tags

    mocker.patch.object(mercurial, "get_existing_tags", new=get_existing_tags)
    assert await mercurial.check_tags(config, tag_info, tmpdir) == expected


@pytest.mark.asyncio
async def test_do_tagging_DONTBUILD_true(config, task, mocker):
    called_args = []

    async def run_command(config, *arguments, repo_path=None, **kwargs):
        called_args.append([tuple([config]) + arguments, {"repo_path": repo_path}])

    mocker.patch.object(mercurial, "run_hg_command", new=run_command)
    mocked_tag_info = mocker.patch.object(mercurial, "get_tag_info")
    mocked_tag_info.return_value = {"revision": "deadbeef", "tags": ["TAG1", "TAG2"]}
    mocked_source_repo = mocker.patch.object(mercurial, "get_source_repo")
    mocked_source_repo.return_value = "https://hg.mozilla.org/treescript-test"
    mocked_dontbuild = mocker.patch.object(mercurial, "get_dontbuild")
    mocked_dontbuild.return_value = True
    mocker.patch.object(mercurial, "check_tags", new=check_tags)
    await mercurial.do_tagging(config, task, config["work_dir"])

    assert len(called_args) == 2
    assert "repo_path" in called_args[0][1]
    assert "repo_path" in called_args[1][1]
    command = called_args[1][0]
    commit_msg = command[command.index("-m") + 1]
    assert DONTBUILD_MSG in commit_msg
    assert is_slice_in_list(("pull", "-r", "deadbeef"), called_args[0][0])
    assert is_slice_in_list(("-r", "deadbeef"), called_args[1][0])
    assert is_slice_in_list(("TAG1", "TAG2"), called_args[1][0])


@pytest.mark.asyncio
async def test_do_tagging_DONTBUILD_false(config, task, mocker):
    called_args = []

    async def run_command(config, *arguments, repo_path=None):
        called_args.append([tuple([config]) + arguments, {"repo_path": repo_path}])

    mocker.patch.object(mercurial, "run_hg_command", new=run_command)
    mocked_tag_info = mocker.patch.object(mercurial, "get_tag_info")
    mocked_tag_info.return_value = {"revision": "deadbeef", "tags": ["TAG1", "TAG2"]}
    mocked_source_repo = mocker.patch.object(mercurial, "get_source_repo")
    mocked_source_repo.return_value = "https://hg.mozilla.org/treescript-test"
    mocked_dontbuild = mocker.patch.object(mercurial, "get_dontbuild")
    mocked_dontbuild.return_value = False
    mocker.patch.object(mercurial, "check_tags", new=check_tags)
    await mercurial.do_tagging(config, task, config["work_dir"])

    assert len(called_args) == 2
    assert "repo_path" in called_args[0][1]
    assert "repo_path" in called_args[1][1]
    command = called_args[1][0]
    commit_msg = command[command.index("-m") + 1]
    assert DONTBUILD_MSG not in commit_msg
    assert is_slice_in_list(("pull", "-r", "deadbeef"), called_args[0][0])
    assert is_slice_in_list(("-r", "deadbeef"), called_args[1][0])
    assert is_slice_in_list(("TAG1", "TAG2"), called_args[1][0])


@pytest.mark.asyncio
async def test_do_tagging_no_tags(config, task, mocker):
    """do_tagging is noop when check_tags returns an empty list."""

    async def check_tags(*args):
        return []

    async def run_command(config, *arguments, repo_path=None):
        assert False, "we shouldn't hit this."

    mocker.patch.object(mercurial, "run_hg_command", new=run_command)
    mocked_tag_info = mocker.patch.object(mercurial, "get_tag_info")
    mocked_tag_info.return_value = {"revision": "deadbeef", "tags": ["TAG1", "TAG2"]}
    mocked_source_repo = mocker.patch.object(mercurial, "get_source_repo")
    mocked_source_repo.return_value = "https://hg.mozilla.org/treescript-test"
    mocked_dontbuild = mocker.patch.object(mercurial, "get_dontbuild")
    mocked_dontbuild.return_value = False
    mocker.patch.object(mercurial, "check_tags", new=check_tags)
    await mercurial.do_tagging(config, task, config["work_dir"])


# log_outgoing {{{1
@pytest.mark.parametrize(
    "output, expected",
    (
        ("", 0),
        (
            """
blah
changeset: x
blah
blah
changeset: 9
blah
    """,
            2,
        ),
    ),
)
def test_count_outgoing(output, expected):
    assert mercurial._count_outgoing(output) == expected


@pytest.mark.parametrize("output", ("somerevision"))
@pytest.mark.asyncio
async def test_get_revision(config, task, mocker, output):
    called_args = []

    async def run_command(config, *arguments, repo_path=None, **kwargs):
        called_args.append([tuple([config]) + arguments, {"repo_path": repo_path}])
        if output:
            return output

    mocker.patch.object(mercurial, "run_hg_command", new=run_command)

    assert output == await mercurial.get_revision(config, config["work_dir"], branch="default")
    assert "repo_path" in called_args[0][1]
    assert is_slice_in_list(("identify", "-r", "default", "--template", "{node}"), called_args[0][0])


@pytest.mark.parametrize("output", ("hg output!", None))
@pytest.mark.asyncio
async def test_log_outgoing(config, task, mocker, output):
    called_args = []

    async def run_command(config, *arguments, repo_path=None, **kwargs):
        called_args.append([tuple([config]) + arguments, {"repo_path": repo_path}])
        if output:
            return output

    mocker.patch.object(mercurial, "run_hg_command", new=run_command)
    mocked_source_repo = mocker.patch.object(mercurial, "get_source_repo")
    mocked_source_repo.return_value = "https://hg.mozilla.org/treescript-test"
    await mercurial.log_outgoing(config, task, config["work_dir"])

    assert len(called_args) == 1
    assert "repo_path" in called_args[0][1]
    assert is_slice_in_list(("out", "-vp"), called_args[0][0])
    assert is_slice_in_list(("-r", "."), called_args[0][0])
    assert "https://hg.mozilla.org/treescript-test" in called_args[0][0]
    if output:
        with open(os.path.join(config["artifact_dir"], "public", "logs", "outgoing.diff"), "r") as fh:
            assert fh.read().rstrip() == output


# strip_outgoing {{{1
@pytest.mark.asyncio
async def test_strip_outgoing(config, task, mocker):
    called_args = []

    async def run_command(config, *arguments, repo_path=None, **kwargs):
        called_args.append([tuple([config]) + arguments, {"repo_path": repo_path}])

    mocker.patch.object(mercurial, "run_hg_command", new=run_command)
    await mercurial.strip_outgoing(config, task, config["work_dir"])

    assert len(called_args) == 3
    assert "repo_path" in called_args[0][1]
    assert is_slice_in_list(("strip", "--no-backup", "outgoing()"), called_args[0][0])


# push {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize("source_repo,revision", ((None, None), ("https://hg.mozilla.org/treescript-test", None), (None, ".")))
async def test_push(config, task, mocker, tmpdir, source_repo, revision):
    called_args = []

    async def run_command(config, *arguments, repo_path=None, **kwargs):
        called_args.append([tuple([config]) + arguments, {"repo_path": repo_path}])

    mocker.patch.object(mercurial, "run_hg_command", new=run_command)
    mocked_source_repo = mocker.patch.object(mercurial, "get_source_repo")
    mocked_source_repo.return_value = "https://hg.mozilla.org/treescript-test"
    await mercurial.push(config, task, tmpdir, source_repo, revision)

    assert len(called_args) == 1
    assert "repo_path" in called_args[0][1]
    assert is_slice_in_list(("push", "-r", "."), called_args[0][0])
    assert "ssh://hg.mozilla.org/treescript-test" in called_args[0][0]
    assert "-e" not in called_args[0][0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "options,expect",
    (
        ({"hg_ssh_keyfile": "/tmp/ffxbld.rsa"}, "ssh -i /tmp/ffxbld.rsa"),
        ({"hg_ssh_user": "ffxbld"}, "ssh -l ffxbld"),
        ({"hg_ssh_keyfile": "/tmp/stage.pub", "hg_ssh_user": "stage_ffxbld"}, "ssh -l stage_ffxbld -i /tmp/stage.pub"),
    ),
)
async def test_push_ssh(config, task, mocker, options, expect, tmpdir):
    called_args = []

    async def run_command(config, *arguments, repo_path=None, **kwargs):
        called_args.append([tuple([config]) + arguments, {"repo_path": repo_path}])

    print()
    config.update(options)
    mocker.patch.object(mercurial, "run_hg_command", new=run_command)
    mocked_source_repo = mocker.patch.object(mercurial, "get_source_repo")
    mocked_source_repo.return_value = "https://hg.mozilla.org/treescript-test"
    await mercurial.push(config, task, tmpdir)

    assert len(called_args) == 1
    assert "repo_path" in called_args[0][1]
    assert is_slice_in_list(("-r", "."), called_args[0][0])
    assert "ssh://hg.mozilla.org/treescript-test" in called_args[0][0]
    assert is_slice_in_list(("push", "-e", expect), called_args[0][0])


@pytest.mark.asyncio
async def test_push_fail(config, task, mocker, tmpdir):
    """Raise a PushError in run_hg_command and verify we clean up."""
    called_args = []

    async def blow_up(*args, **kwargs):
        raise PushError("x")

    async def clean_up(*args):
        assert args == (config, task, tmpdir)
        called_args.append(args)

    mocker.patch.object(mercurial, "run_hg_command", new=blow_up)
    mocker.patch.object(mercurial, "strip_outgoing", new=clean_up)
    with pytest.raises(PushError):
        await mercurial.push(config, task, tmpdir)
    assert len(called_args) == 1
