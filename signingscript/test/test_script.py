import json
import mock
import os
import pytest
import sys

import scriptworker.client
from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException
from signingscript.test import noop_async, noop_sync, read_file, tmpdir, tmpfile, BASE_DIR
import signingscript.script as script
from unittest.mock import MagicMock

assert tmpdir  # silence flake8

# helper constants, fixtures, functions {{{1
EXAMPLE_CONFIG = os.path.join(BASE_DIR, 'config_example.json')
SSL_CERT = os.path.join(BASE_DIR, "signingscript", "data", "host.cert")


# async_main {{{1
async def async_main_helper(tmpdir, mocker, formats, extra_config={}, server_type=script.SigningServerType.cert):

    def fake_filelist_dict(*args, **kwargs):
        return {'path1': {'full_path': 'full_path1', 'formats': formats}}

    async def fake_sign(_, val, *args):
        return [val]

    mocker.patch.object(script, 'load_signing_server_config', new=noop_sync)
    mocker.patch.object(script, 'task_server_type', return_value=server_type.name)
    mocker.patch.object(script, 'task_signer_type', new=noop_sync)
    mocker.patch.object(script, 'task_signing_formats', return_value=formats)
    mocker.patch.object(script, 'get_token', new=noop_async)
    mocker.patch.object(script, 'build_filelist_dict', new=fake_filelist_dict)
    mocker.patch.object(script, 'sign', new=fake_sign)
    context = mock.MagicMock()
    context.config = {
        'work_dir': tmpdir, 'ssl_cert': None, 'artifact_dir': tmpdir,
    }
    context.config.update(extra_config)
    await script.async_main(context)


@pytest.mark.asyncio
async def test_async_main_gpg(tmpdir, mocker):
    formats = ['gpg']
    fake_gpg_pubkey = tmpfile()
    mocked_copy_to_dir = mocker.Mock()
    mocker.patch.object(script, 'copy_to_dir', new=mocked_copy_to_dir)

    await async_main_helper(tmpdir, mocker, formats, {'gpg_pubkey': fake_gpg_pubkey})
    for call in mocked_copy_to_dir.call_args_list:
        if call[1].get('target') == 'public/build/KEY':
            break
    else:
        assert False, "couldn't find copy_to_dir call that created KEY"
    os.remove(fake_gpg_pubkey)


@pytest.mark.asyncio
async def test_async_main_gpg_no_pubkey_defined(tmpdir, mocker):
    formats = ['gpg']

    try:
        await async_main_helper(tmpdir, mocker, formats)
    except Exception as e:
        assert e.args[0] == "GPG format is enabled but gpg_pubkey is not defined"


@pytest.mark.asyncio
async def test_async_main_gpg_pubkey_doesnt_exist(tmpdir, mocker):
    formats = ['gpg']

    try:
        await async_main_helper(tmpdir, mocker, formats, {'gpg_pubkey': 'faaaaaaake'})
    except Exception as e:
        assert e.args[0] == "gpg_pubkey (faaaaaaake) doesn't exist!"


@pytest.mark.asyncio
async def test_async_main_multiple_formats(tmpdir, mocker):
    formats = ['mar', 'jar']
    mocker.patch.object(script, 'copy_to_dir', new=noop_sync)
    await async_main_helper(tmpdir, mocker, formats)


@pytest.mark.asyncio
async def test_async_main_autograph(tmpdir, mocker):
    formats = ['mar']
    mocker.patch.object(script, 'task_signer_type', new=noop_sync)
    mocker.patch.object(script, 'copy_to_dir', new=noop_sync)
    await async_main_helper(tmpdir, mocker, formats, {}, script.SigningServerType.autograph)


def test_craft_aiohttp_connector():
    context = Context()
    context.config = {}
    connector = script._craft_aiohttp_connector(context)
    assert connector._ssl is None

    context.config['ssl_cert'] = SSL_CERT
    connector = script._craft_aiohttp_connector(context)
    assert connector._ssl


def test_get_default_config():
    parent_dir = os.path.dirname(os.getcwd())
    c = script.get_default_config()
    assert c['work_dir'] == os.path.join(parent_dir, 'work_dir')


def test_main(monkeypatch):
    sync_main_mock = MagicMock()
    monkeypatch.setattr(scriptworker.client, 'sync_main', sync_main_mock)
    script.main()
    sync_main_mock.asset_called_once_with(script.async_main, default_config=script.get_default_config())
