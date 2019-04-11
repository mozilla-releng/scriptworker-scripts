#!/usr/bin/env python
# coding=utf-8
"""Test iscript.script
"""
import os
import pytest
from iscript.exceptions import IScriptError
import iscript.script as script


# async_main {{{1
@pytest.mark.parametrize(
    "behavior, supported_behaviors, expected_behavior, raises",
    (
        ("mac_pkg", ["mac_sign", "mac_pkg"], "mac_pkg", False),
        ("mac_notarize", ["mac_sign", "mac_notarize"], "mac_notarize", False),
        ("mac_notarize", ["mac_sign", "mac_sign_and_pkg"], "mac_sign_and_pkg", False),
        ("mac_sign", ["mac_sign"], "mac_sign", False),
        ("mac_sign", ["mac_sign"], "mac_sign", False),
        (
            "mac_sign_and_pkg",
            ["mac_pkg", "mac_sign_and_pkg"],
            "mac_sign_and_pkg",
            False,
        ),
        (None, ["mac_sign"], "mac_sign", False),
        ("invalid_behavior", ["mac_sign", "invalid_behavior"], None, True),
        ("mac_notarize", ["mac_sign", "mac_pkg"], None, True),
    ),
)
@pytest.mark.asyncio
async def test_async_main(
    mocker, behavior, supported_behaviors, expected_behavior, raises
):
    """``async_main`` calls the appropriate function based on behavior

    """

    calls = {}
    config = {"a": "b"}
    task = {"c": "d", "payload": {}, "scopes": []}
    if behavior:
        task["payload"]["behavior"] = behavior
    expected = [[(config, task), {}]]
    key_config = {"supported_behaviors": supported_behaviors}

    async def test_notarize(*args, **kwargs):
        calls.setdefault("mac_notarize", []).append([args, kwargs])

    async def test_pkg(*args, **kwargs):
        calls.setdefault("mac_pkg", []).append([args, kwargs])

    async def test_sign(*args, **kwargs):
        calls.setdefault("mac_sign", []).append([args, kwargs])

    async def test_sign_and_pkg(*args, **kwargs):
        calls.setdefault("mac_sign_and_pkg", []).append([args, kwargs])

    mocker.patch.object(script, "notarize_behavior", new=test_notarize)
    mocker.patch.object(script, "pkg_behavior", new=test_pkg)
    mocker.patch.object(script, "sign_behavior", new=test_sign)
    mocker.patch.object(script, "sign_and_pkg_behavior", new=test_sign_and_pkg)
    mocker.patch.object(script, "get_key_config", return_value=key_config)
    if raises:
        with pytest.raises(IScriptError):
            await script.async_main(config, task)
    else:
        await script.async_main(config, task)
        assert calls.get(expected_behavior) == expected


# get_default_config {{{1
def test_get_default_config(tmpdir):
    """``get_default_config`` returns a dict with expected keys/values.

    """
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
