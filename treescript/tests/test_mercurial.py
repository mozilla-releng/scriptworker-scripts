"""Tests for mercurial functionality.

We don't test the robustcheckout extension here, nor is this file about integration
testing with mercurial commands, we are testing that we can call mercurial and that
it's expected output is something our script can cope with.

"""

import os

import pytest
from scriptworker_client.utils import makedirs
from treescript import mercurial
from treescript.exceptions import FailedSubprocess
from treescript.script import get_default_config
from treescript.utils import DONTBUILD_MSG


ROBUSTCHECKOUT_FILE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "src", "treescript", "py2", "robustcheckout.py"
    )
)
UNEXPECTED_ENV_KEYS = (
    "HG HGPROF CDPATH GREP_OPTIONS http_proxy no_proxy "
    "HGPLAINEXCEPT EDITOR VISUAL PAGER NO_PROXY CHGDEBUG".split()
)


@pytest.yield_fixture(scope="function")
def task():
    return {"metadata": {"source": "https://hg.mozilla.org/repo-name/file/filename"}}


async def noop_async(*args, **kwargs):
    pass


def is_slice_in_list(s, l):
    # Credit to https://stackoverflow.com/a/20789412/#answer-20789669
    # With edits by Callek to be py3 and pep8 compat
    len_s = len(s)  # so we don't recompute length of s on every iteration
    return any(s == l[i: len_s + i] for i in range(len(l) - len_s + 1))


@pytest.yield_fixture(scope="function")
def config(tmpdir):
    config = get_default_config()
    config["work_dir"] = os.path.join(tmpdir, "work")
    config["artifact_dir"] = os.path.join(tmpdir, "artifact")
    makedirs(config["work_dir"])
    makedirs(config["artifact_dir"])
    yield config


@pytest.mark.parametrize(
    "hg,args", (("hg", ["blah", "blah", "--baz"]), (["hg"], ["blah", "blah", "--baz"]))
)
def test_build_hg_cmd(config, hg, args):
    config["hg"] = hg
    assert mercurial.build_hg_command(config, *args) == [
        "hg",
        "--config",
        "extensions.robustcheckout={}".format(ROBUSTCHECKOUT_FILE),
        "blah",
        "blah",
        "--baz",
    ]


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
    assert called_args[0] == [
        ["hg"] + args,
        {"env": env, "exception": FailedSubprocess},
    ]
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

    await mercurial.run_hg_command(config, *args, local_repo="/tmp/localrepo")

    env_call.assert_called_with()
    cmd_call.assert_called_with(config, *args)
    assert len(called_args) == 1
    is_slice_in_list(["-R", "/tmp/localrepo"], called_args[0][0])


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


@pytest.mark.asyncio
async def test_checkout_repo(config, task, mocker):
    async def check_params(*args, **kwargs):
        assert is_slice_in_list(("--sharebase", "/builds/hg-shared-test"), args)
        assert is_slice_in_list(
            (
                "robustcheckout",
                "https://hg.mozilla.org/test-repo",
                os.path.join(config["work_dir"], "src"),
            ),
            args,
        )

    mocker.patch.object(mercurial, "run_hg_command", new=check_params)
    mocker.patch.object(
        mercurial, "get_source_repo"
    ).return_value = "https://hg.mozilla.org/test-repo"

    config["hg_share_base_dir"] = "/builds/hg-shared-test"
    config["upstream_repo"] = "https://hg.mozilla.org/mozilla-test-unified"

    await mercurial.checkout_repo(config, task, config["work_dir"])


@pytest.mark.asyncio
async def test_do_tagging_DONTBUILD_true(config, task, mocker):
    called_args = []

    async def run_command(config, *arguments, local_repo=None):
        called_args.append([tuple([config]) + arguments, {"local_repo": local_repo}])

    mocker.patch.object(mercurial, "run_hg_command", new=run_command)
    mocked_tag_info = mocker.patch.object(mercurial, "get_tag_info")
    mocked_tag_info.return_value = {"revision": "deadbeef", "tags": ["TAG1", "TAG2"]}
    mocked_source_repo = mocker.patch.object(mercurial, "get_source_repo")
    mocked_source_repo.return_value = "https://hg.mozilla.org/treescript-test"
    mocked_dontbuild = mocker.patch.object(mercurial, "get_dontbuild")
    mocked_dontbuild.return_value = True
    await mercurial.do_tagging(config, task, config["work_dir"])

    assert len(called_args) == 2
    assert "local_repo" in called_args[0][1]
    assert "local_repo" in called_args[1][1]
    command = called_args[1][0]
    commit_msg = command[command.index("-m") + 1]
    assert DONTBUILD_MSG in commit_msg
    assert is_slice_in_list(("pull", "-r", "deadbeef"), called_args[0][0])
    assert is_slice_in_list(("-r", "deadbeef"), called_args[1][0])
    assert is_slice_in_list(("TAG1", "TAG2"), called_args[1][0])


@pytest.mark.asyncio
async def test_do_tagging_DONTBUILD_false(config, task, mocker):
    called_args = []

    async def run_command(config, *arguments, local_repo=None):
        called_args.append([tuple([config]) + arguments, {"local_repo": local_repo}])

    mocker.patch.object(mercurial, "run_hg_command", new=run_command)
    mocked_tag_info = mocker.patch.object(mercurial, "get_tag_info")
    mocked_tag_info.return_value = {"revision": "deadbeef", "tags": ["TAG1", "TAG2"]}
    mocked_source_repo = mocker.patch.object(mercurial, "get_source_repo")
    mocked_source_repo.return_value = "https://hg.mozilla.org/treescript-test"
    mocked_dontbuild = mocker.patch.object(mercurial, "get_dontbuild")
    mocked_dontbuild.return_value = False
    await mercurial.do_tagging(config, task, config["work_dir"])

    assert len(called_args) == 2
    assert "local_repo" in called_args[0][1]
    assert "local_repo" in called_args[1][1]
    command = called_args[1][0]
    commit_msg = command[command.index("-m") + 1]
    assert DONTBUILD_MSG not in commit_msg
    assert is_slice_in_list(("pull", "-r", "deadbeef"), called_args[0][0])
    assert is_slice_in_list(("-r", "deadbeef"), called_args[1][0])
    assert is_slice_in_list(("TAG1", "TAG2"), called_args[1][0])


@pytest.mark.asyncio
async def test_push(config, task, mocker):
    called_args = []

    async def run_command(config, *arguments, local_repo=None):
        called_args.append([tuple([config]) + arguments, {"local_repo": local_repo}])

    mocker.patch.object(mercurial, "run_hg_command", new=run_command)
    mocked_source_repo = mocker.patch.object(mercurial, "get_source_repo")
    mocked_source_repo.return_value = "https://hg.mozilla.org/treescript-test"
    await mercurial.push(config, task)

    assert len(called_args) == 1
    assert "local_repo" in called_args[0][1]
    assert is_slice_in_list(("push", "-r", "."), called_args[0][0])
    assert "ssh://hg.mozilla.org/treescript-test" in called_args[0][0]
    assert "-e" not in called_args[0][0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "options,expect",
    (
        ({"hg_ssh_keyfile": "/tmp/ffxbld.rsa"}, "ssh -i /tmp/ffxbld.rsa"),
        ({"hg_ssh_user": "ffxbld"}, "ssh -l ffxbld"),
        (
            {"hg_ssh_keyfile": "/tmp/stage.pub", "hg_ssh_user": "stage_ffxbld"},
            "ssh -l stage_ffxbld -i /tmp/stage.pub",
        ),
    ),
)
async def test_push_ssh(config, task, mocker, options, expect):
    called_args = []

    async def run_command(config, *arguments, local_repo=None):
        called_args.append([tuple([config]) + arguments, {"local_repo": local_repo}])

    print()
    config.update(options)
    mocker.patch.object(mercurial, "run_hg_command", new=run_command)
    mocked_source_repo = mocker.patch.object(mercurial, "get_source_repo")
    mocked_source_repo.return_value = "https://hg.mozilla.org/treescript-test"
    await mercurial.push(config, task)

    assert len(called_args) == 1
    assert "local_repo" in called_args[0][1]
    assert is_slice_in_list(("-r", "."), called_args[0][0])
    assert "ssh://hg.mozilla.org/treescript-test" in called_args[0][0]
    assert is_slice_in_list(("push", "-e", expect), called_args[0][0])


@pytest.mark.asyncio
async def test_log_outgoing(config, task, mocker):
    called_args = []

    async def run_command(config, *arguments, local_repo=None):
        called_args.append([tuple([config]) + arguments, {"local_repo": local_repo}])

    mocker.patch.object(mercurial, "run_hg_command", new=run_command)
    mocked_source_repo = mocker.patch.object(mercurial, "get_source_repo")
    mocked_source_repo.return_value = "https://hg.mozilla.org/treescript-test"
    await mercurial.log_outgoing(config, task, config["work_dir"])

    assert len(called_args) == 1
    assert "local_repo" in called_args[0][1]
    assert is_slice_in_list(("out", "-vp"), called_args[0][0])
    assert is_slice_in_list(("-r", "."), called_args[0][0])
    assert is_slice_in_list(
        ("https://hg.mozilla.org/treescript-test",), called_args[0][0]
    )
