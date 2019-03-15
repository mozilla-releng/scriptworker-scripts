#!/usr/bin/env python
# coding=utf-8
"""Test iscript.script
"""
import os
import pytest
import tempfile
import iscript.script as script


# async_main {{{1
@pytest.mark.asyncio
async def test_async_main(mocker):
    """``async_main`` calls ``sign_and_notarize_all``.

    """

    calls = []
    config = {'a': 'b'}
    task = {'c': 'd'}
    expected = [[(config, task), {}]]

    async def test_sign(*args, **kwargs):
        calls.append([args, kwargs])

    mocker.patch.object(script, 'sign_and_notarize_all', new=test_sign)
    await script.async_main(config, task)
    assert calls == expected


# get_default_config {{{1
def test_get_default_config():
    """``get_default_config`` returns a dict with expected keys/values.

    """
    with tempfile.TemporaryDirectory() as tmp:
        config = script.get_default_config(base_dir=tmp)
        assert config['work_dir'] == os.path.join(tmp, 'work')
        for k in ('artifact_dir', 'schema_file'):
            assert k in config


# main {{{1
@pytest.mark.asyncio
async def test_main(mocker):
    """``main`` calls ``sync_main`` with ``async_main`` and ``default_config``.

    This function is async because we have an async helper function inside.
    """

    calls = []
    config = {'a': 'b'}

    def fake_main(*args, **kwargs):
        calls.append([args, kwargs])

    def fake_config():
        return config

    async def fake_async_main(*args, **kwargs):
        pass

    mocker.patch.object(script, 'sync_main', new=fake_main)
    mocker.patch.object(script, 'async_main', new=fake_async_main)
    mocker.patch.object(script, 'get_default_config', new=fake_config)
    script.main()
    assert calls == [[(fake_async_main, ), {'default_config': config}]]
