"""Robustcheckout itself is tested via version control tools,

We use a vendored copy, tests here are merely about integration with our tooling.

"""

import os

import pytest
from scriptworker.context import Context
from treescript import mercurial
from treescript.exceptions import FailedSubprocess
from treescript.script import get_default_config
from treescript.utils import mkdir
from treescript.test import tmpdir, noop_async
from treescript import utils

assert tmpdir  # silence flake8


ROBUSTCHECKOUT_FILE = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'py2', 'robustcheckout.py'
))
UNEXPECTED_ENV_KEYS = ('HG HGPROF CDPATH GREP_OPTIONS http_proxy no_proxy '
                       'HGPLAINEXCEPT EDITOR VISUAL PAGER NO_PROXY CHGDEBUG'.split())


@pytest.yield_fixture(scope='function')
def context(tmpdir):
    context = Context()
    context.config = get_default_config()
    context.config['work_dir'] = os.path.join(tmpdir, 'work')
    context.config['artifact_dir'] = os.path.join(tmpdir, 'artifact')
    mkdir(context.config['work_dir'])
    mkdir(context.config['artifact_dir'])
    yield context


@pytest.mark.parametrize('hg,args', ((
    "hg", ["blah", "blah", "--baz"]
), (
    ["hg"], ["blah", "blah", "--baz"]
)))
def test_build_hg_cmd(context, hg, args):
    context.config['hg'] = hg
    assert mercurial.build_hg_command(context, *args) == [
        "hg",
        "--config", "extensions.robustcheckout={}".format(ROBUSTCHECKOUT_FILE),
        "blah", "blah", "--baz"
    ]


@pytest.mark.parametrize('my_env', ({
    # Blank
}, {  # defaults wrong
    "HGPLAIN": "0",
    "LANG": "en_US.utf8"
}, {  # Values to strip from env
    k: "whatever" for k in UNEXPECTED_ENV_KEYS
}
))
def test_build_hg_env(mocker, my_env):
    mocker.patch.dict(mercurial.os.environ, my_env)
    returned_env = mercurial.build_hg_environment()
    assert (set(UNEXPECTED_ENV_KEYS) & set(returned_env.keys())) == set()
    assert returned_env['HGPLAIN'] == "1"
    assert returned_env['LANG'] == "C"
    for key in returned_env.keys():
        assert type(returned_env[key]) == str


@pytest.mark.asyncio
@pytest.mark.parametrize('args', (['foobar', '--bar'], ['--test', 'args', 'banana']))
async def test_run_hg_command(mocker, context, args):
    called_args = []

    async def run_command(*arguments, **kwargs):
        called_args.append([*arguments, kwargs])

    mocker.patch.object(mercurial, 'execute_subprocess', new=run_command)
    env_call = mocker.patch.object(mercurial, 'build_hg_environment')
    cmd_call = mocker.patch.object(mercurial, 'build_hg_command')
    env = {'HGPLAIN': 1, 'LANG': 'C'}
    env_call.return_value = env
    cmd_call.return_value = ['hg', *args]

    await mercurial.run_hg_command(context, *args)

    env_call.assert_called_with()
    cmd_call.assert_called_with(context, *args)
    assert called_args[0] == [['hg'] + args, {'env': env}]
    assert len(called_args) == 1


@pytest.mark.asyncio
async def test_hg_version(context, mocker):
    logged = []

    def info(msg):
        logged.append(msg)

    mocklog = mocker.patch.object(utils, 'log')
    mocklog.info = info
    await mercurial.log_mercurial_version(context)

    assert 'Mercurial Distributed SCM (version' in logged[2]


@pytest.mark.asyncio
async def test_validate_robustcheckout_works(context, mocker):
    mocker.patch.object(mercurial, 'run_hg_command', new=noop_async)
    ret = await mercurial.validate_robustcheckout_works(context)
    assert ret is True


@pytest.mark.asyncio
async def test_validate_robustcheckout_works_doesnt(context, mocker):
    mocked = mocker.patch.object(mercurial, 'run_hg_command')
    mocked.side_effect = FailedSubprocess('Mocked failure in test harness')
    ret = await mercurial.validate_robustcheckout_works(context)
    assert ret is False


@pytest.mark.asyncio
async def test_checkout_repo(context, mocker):
    def _is_slice_in_list(s, l):
        # Credit to https://stackoverflow.com/a/20789412/#answer-20789669
        # With edits by Callek to be py3 and pep8 compat
        len_s = len(s)  # so we don't recompute length of s on every iteration
        return any(s == l[i:len_s + i] for i in range(len(l) - len_s + 1))

    async def check_params(*args, **kwargs):
        assert _is_slice_in_list(('--sharebase', '/builds/hg-shared-test'), args)
        assert _is_slice_in_list(('robustcheckout', 'https://hg.mozilla.org/test-repo',
                                  os.path.join(context.config['work_dir'], 'src')),
                                 args)

    mocker.patch.object(mercurial, 'run_hg_command', new=check_params)
    mocker.patch.object(mercurial, 'get_source_repo').return_value = "https://hg.mozilla.org/test-repo"

    context.config['hg_share_base_dir'] = '/builds/hg-shared-test'
    context.config['upstream_repo'] = 'https://hg.mozilla.org/mozilla-test-unified'

    await mercurial.checkout_repo(context, context.config['work_dir'])
