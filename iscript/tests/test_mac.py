#!/usr/bin/env python
# coding=utf-8
"""Test iscript.mac
"""
import os
import pytest
import iscript.mac as mac
from iscript.exceptions import IScriptError


# helpers {{{1
async def noop_async(*args, **kwargs):
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
    mocker.patch.object(mac, 'run_command', new=noop_async)
