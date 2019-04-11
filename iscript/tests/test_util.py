#!/usr/bin/env python
# coding=utf-8
"""Test iscript.util
"""
import pytest
import iscript.util as util
from iscript.exceptions import IScriptError


# get_key_config {{{1
@pytest.mark.parametrize(
    "scopes, base_key, key, raises",
    (
        (("scope:prefix:cert:dep-signing",), "mac_config", "dep", False),
        (("scope:prefix:cert:nightly-signing",), "mac_config", "nightly", False),
        (("invalid_scope"), "mac_config", None, True),
        (
            ["scope:prefix:cert:nightly-signing", "scope:prefix:cert:dep-signing"],
            "mac_config",
            "",
            True,
        ),
        (("scope:prefix:cert:dep-signing",), "invalid_base_key", "", True),
    ),
)
def test_get_config_key(scopes, base_key, key, raises):
    """``get_config_key`` returns the correct subconfig.

    """
    config = {
        "taskcluster_scope_prefix": "scope:prefix:",
        "mac_config": {"dep": {"key": "dep"}, "nightly": {"key": "nightly"}},
    }
    task = {"scopes": scopes}
    if raises:
        with pytest.raises(IScriptError):
            util.get_key_config(config, task, base_key=base_key)
    else:
        assert (
            util.get_key_config(config, task, base_key=base_key)
            == config[base_key][key]
        )
