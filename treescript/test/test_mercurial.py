"""Robustcheckout itself is tested via version control tools,

We use a vendored copy, tests here are merely about integration with our tooling.

"""

import os

import pytest
from scriptworker.context import Context
from treescript import mercurial
from treescript.script import get_default_config
from treescript.utils import mkdir
from treescript.test import tmpdir

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
