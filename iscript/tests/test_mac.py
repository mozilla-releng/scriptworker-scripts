#!/usr/bin/env python
# coding=utf-8
"""Test iscript.mac
"""
import os
import pytest
import iscript.mac as mac
from iscript.exceptions import IScriptError
from scriptworker_client.utils import makedirs


# helpers {{{1
async def noop_async(*args, **kwargs):
    pass


def touch(path):
    parent_dir = os.path.dirname(path)
    makedirs(parent_dir)
    with open(path, 'w') as fh:
        pass


# App {{{1
def test_app():
    """``App`` attributes can be set, and ``check_required_attrs`` raises if
    the required attrs aren't set.

    """
    a = mac.App()
    assert a.orig_path == ''
    a.orig_path = 'foo'
    assert a.orig_path == 'foo'
    a.check_required_attrs(['orig_path'])
    with pytest.raises(IScriptError):
        a.check_required_attrs(['app_path'])


# sign {{{1
@pytest.mark.asyncio
async def test_sign(mocker, tmpdir):
    """Render ``sign`` noop and verify we have complete code coverage.

    """
    config = {
        'mac_config': {
            'key': {
                'identity': 'id',
            },
        },
    }
    app = mac.App()
    app.parent_dir = str(tmpdir)
    entitlements_path = os.path.join(tmpdir, 'entitlements')
    app_path = os.path.join(tmpdir, 'foo.app')
    for p in list(mac.INITIAL_FILES_TO_SIGN) + ['Resources/MacOS/foo']:
        p = p.replace('*', 'foo')
        touch(os.path.join(app_path, p))
    mocker.patch.object(mac, 'run_command', new=noop_async)
    await mac.sign(config, app, 'key', entitlements_path)
