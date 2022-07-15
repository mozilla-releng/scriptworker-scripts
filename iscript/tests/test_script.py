#!/usr/bin/env python
# coding=utf-8
"""Test iscript.script
"""
import os

import pytest

import iscript.script as script
from iscript.exceptions import IScriptError


# async_main {{{1
@pytest.mark.parametrize(
    "behavior, supported_behaviors, expected_behavior, raises",
    (
        ("mac_single_file", ["mac_sign", "mac_single_file"], "mac_single_file", False),
        ("mac_notarize", ["mac_sign", "mac_notarize"], "mac_notarize", False),
        ("mac_notarize", ["mac_sign", "mac_notarize", "mac_sign_and_pkg"], "mac_notarize", False),
        ("mac_notarize_vpn", ["mac_notarize_vpn", "mac_sign_and_pkg_vpn"], "mac_notarize_vpn", False),
        ("mac_notarize_vpn", ["mac_sign_and_pkg_vpn"], "mac_sign_and_pkg_vpn", False),
        ("mac_notarize", ["mac_sign", "mac_sign_and_pkg"], "mac_sign_and_pkg", False),
        ("mac_sign", ["mac_sign"], "mac_sign", False),
        ("mac_sign_and_pkg", ["mac_single_file", "mac_sign_and_pkg"], "mac_sign_and_pkg", False),
        (None, ["mac_sign"], "mac_sign", False),
        ("invalid_behavior", ["mac_sign", "invalid_behavior"], None, True),
        ("mac_notarize", ["mac_sign", "mac_single_file"], None, True),
        ("mac_notarize_part_1", ["mac_notarize_part_1", "mac_single_file"], "mac_notarize_part_1", False),
        ("mac_notarize_part_3", ["mac_notarize_part_3", "mac_single_file"], "mac_notarize_part_3", False),
    ),
)
@pytest.mark.asyncio
async def test_async_main(mocker, behavior, supported_behaviors, expected_behavior, raises):
    """``async_main`` calls the appropriate function based on behavior"""

    calls = {}
    config = {"a": "b"}
    task = {"c": "d", "payload": {}, "scopes": []}
    if behavior:
        task["payload"]["behavior"] = behavior
    expected = [[(config, task), {}]]

    # Accounts for notarizing True/False
    if behavior == "mac_notarize_vpn":
        expected = [[(config, task), {"notarize": "mac_notarize_vpn" in supported_behaviors}]]
    elif behavior == "mac_single_file":
        expected = [[(config, task), {"notarize": "mac_notarize_single_file" in supported_behaviors}]]

    sign_config = {"supported_behaviors": supported_behaviors}

    original_func = script.get_behavior_function

    def test_get_behavior_function(behav):
        async def mocked_behavior(*args, **kwargs):
            calls.setdefault(behav, []).append([args, kwargs])

        _, fargs = original_func(behav)
        return (mocked_behavior, fargs)

    mocker.patch.object(script, "get_behavior_function", new=test_get_behavior_function)
    mocker.patch.object(script, "get_sign_config", return_value=sign_config)
    if raises:
        with pytest.raises(IScriptError):
            await script.async_main(config, task)
    else:
        await script.async_main(config, task)
        assert calls.get(expected_behavior) == expected


# get_default_config {{{1
def test_get_default_config(tmpdir):
    """``get_default_config`` returns a dict with expected keys/values."""
    config = script.get_default_config(base_dir=tmpdir)
    assert config["work_dir"] == os.path.join(tmpdir, "work")
    for k in ("artifact_dir", "schema_file"):
        assert k in config


# main {{{1
@pytest.mark.asyncio
async def test_main(mocker):
    """``main`` calls ``sync_main`` with ``async_main`` and ``default_config``.

    This function is async because we have an async helper function inside.
    """

    calls = []
    config = {"a": "b"}

    def fake_main(*args, **kwargs):
        calls.append([args, kwargs])

    def fake_config():
        return config

    async def fake_async_main(*args, **kwargs):
        pass

    mocker.patch.object(script, "sync_main", new=fake_main)
    mocker.patch.object(script, "async_main", new=fake_async_main)
    mocker.patch.object(script, "get_default_config", new=fake_config)
    script.main()
    assert calls == [[(fake_async_main,), {"default_config": config}]]
