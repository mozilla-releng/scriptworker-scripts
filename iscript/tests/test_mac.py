#!/usr/bin/env python
# coding=utf-8
"""Test iscript.mac
"""
import os
import pytest
import tempfile
import iscript.mac as mac
from iscript.exceptions import IScriptError


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
