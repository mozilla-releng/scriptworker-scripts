"""Treescript mercurial functions."""
# import asyncio
# from asyncio.subprocess import PIPE, STDOUT
# import functools
# import hashlib
# import json
# import logging
import os
import sys
# from shutil import copyfile
# import traceback
# from collections import namedtuple

from treescript.utils import execute_subprocess
from treescript.exceptions import FailedSubprocess

# https://www.mercurial-scm.org/repo/hg/file/tip/tests/run-tests.py#l1040
# For environment vars.

HGRCPATH = os.path.join(os.path.dirname(__file__), 'data', 'hgrc')
ROBUSTCHECKOUT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), 'py2', 'robustcheckout.py')
)


def build_hg_command(context, *args):
    """Generate a mercurial command to run.

    See-Also `build_hg_environment`

    Args:
        context (TreeScriptContext): the treescript context
        *str: the remaining args to pass to the hg command

    Returns:
        list: the hg command to run.

    """
    hg = context.config['hg']
    if not isinstance(hg, (list, tuple)):
        hg = [hg]
    robustcheckout_args = [
        '--config', 'extensions.robustcheckout={}'.format(ROBUSTCHECKOUT_PATH)
    ]
    return hg + [*robustcheckout_args, *args]


def build_hg_environment():
    """Generate an environment suitable for running mercurial programtically.

    This function sets the hgrc to one provided in the package and ensures
    environment variables which affect HG are defined in a stable way.

    See-Also `build_hg_command`, `run_hg_command`

    Returns:
        list: the environment to use.

    """
    env = os.environ.copy()
    env['HGRCPATH'] = HGRCPATH
    env['HGEDITOR'] = ('"' + sys.executable + '"' + ' -c "import sys; sys.exit(0)"')
    env["HGMERGE"] = "internal:merge"
    env["HGENCODING"] = "utf-8"
    env['HGPLAIN'] = '1'
    env['LANG'] = env['LC_ALL'] = env['LANGUAGE'] = 'C'
    env['TZ'] = 'GMT'
    # List found at
    # https://www.mercurial-scm.org/repo/hg/file/ab239e3de23b/tests/run-tests.py#l1076
    for k in ('HG HGPROF CDPATH GREP_OPTIONS http_proxy no_proxy ' +
              'HGPLAINEXCEPT EDITOR VISUAL PAGER NO_PROXY CHGDEBUG').split():
        if k in env:
            del env[k]
    return env


async def run_hg_command(context, *args):
    """Run a mercurial command.

    See-Also `build_hg_environment`, `build_hg_command`

    Args:
        context (TreeScriptContext): the treescript context
        *str: the remaining args to pass to the hg command

    Returns:
        list: the hg command to run.

    """
    command = build_hg_command(context, *args)
    env = build_hg_environment()
    await execute_subprocess(command, env=env)


async def log_mercurial_version(context):
    """Run mercurial `-v version` to get used version into logs.

    Args:
        context (TreeScriptContext): the treescript context

    """
    await run_hg_command(context, '-v', 'version')


async def validate_robustcheckout_works(context):
    """Validate that the robustcheckout extension works.

    This works by trying to run `hg robustcheckout -q --help` on
    hg as defined by our context object.

    Args:
        context (TreeScriptContext): the treescript context

    Returns:
        bool: True if robustcheckout seems to work, False otherwise.

    """
    try:
        await run_hg_command(context, 'robustcheckout', '-q', '--help')
        return True
    except FailedSubprocess:
        return False
