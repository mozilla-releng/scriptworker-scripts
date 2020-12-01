#!/usr/bin/env python
# coding=utf-8
"""Test iscript.util
"""
from copy import deepcopy

import pytest

import iscript.util as util
from iscript.constants import PRODUCT_CONFIG
from iscript.exceptions import IScriptError


# get_sign_config {{{1
@pytest.mark.parametrize(
    "scopes, base_key, key, product, raises",
    (
        (("scope:prefix:cert:dep-signing",), "mac_config", "dep", "firefox", False),
        (("scope:prefix:cert:nightly-signing",), "mac_config", "nightly", "firefox", False),
        (("scope:prefix:cert:nightly-signing",), "mac_config", "nightly", "mozillavpn", False),
        (("invalid_scope"), "mac_config", None, "firefox", True),
        (["scope:prefix:cert:nightly-signing", "scope:prefix:cert:dep-signing"], "mac_config", "", "firefox", True),
        (("scope:prefix:cert:dep-signing",), "invalid_base_key", "", "firefox", True),
        (("scope:prefix:cert:dep-signing",), "mac_config", "dep", "bad_product", True),
    ),
)
def test_get_config_key(scopes, base_key, key, product, raises):
    """``get_config_key`` returns the correct subconfig."""
    config = {"taskcluster_scope_prefix": "scope:prefix:", "mac_config": {"dep": {"key": "dep"}, "nightly": {"key": "nightly"}}}
    task = {"scopes": scopes, "payload": {"product": product}}
    if raises:
        with pytest.raises(IScriptError):
            util.get_sign_config(config, task, base_key=base_key)
    else:
        sign_config = util.get_sign_config(config, task, base_key=base_key)
        expected = deepcopy(PRODUCT_CONFIG[base_key][product])
        expected.update(config[base_key][key])
        assert sign_config == expected
