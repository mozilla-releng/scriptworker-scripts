import json
import mock
import os
import pytest
import sys

import scriptworker.client
from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException
from signingscript.test import noop_async, noop_sync, read_file, tmpdir, BASE_DIR
import signingscript.script as script
from unittest.mock import MagicMock

assert tmpdir  # silence flake8

# helper constants, fixtures, functions {{{1
EXAMPLE_CONFIG = os.path.join(BASE_DIR, 'config_example.json')
SSL_CERT = os.path.join(BASE_DIR, "signingscript", "data", "host.cert")


def get_conf_file(tmpdir, **kwargs):
    conf = json.loads(read_file(EXAMPLE_CONFIG))
    conf.update(kwargs)
    conf['work_dir'] = os.path.join(tmpdir, 'work')
    conf['artifact_dir'] = os.path.join(tmpdir, 'artifact')
    path = os.path.join(tmpdir, "new_config.json")
    with open(path, "w") as fh:
        json.dump(conf, fh)
    return path


async def die_async(*args, **kwargs):
    raise ScriptWorkerTaskException("Expected exception.")


# async_main {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize('formats', (['gpg'], ['mar', 'jar']))
async def test_async_main(tmpdir, mocker, formats):

    def fake_filelist_dict(*args, **kwargs):
        return {'path1': {'full_path': 'full_path1', 'formats': formats}}

    async def fake_sign(_, val, *args):
        return [val]

    mocker.patch.object(script, 'load_signing_server_config', new=noop_sync)
    mocker.patch.object(script, 'task_cert_type', new=noop_sync)
    mocker.patch.object(script, 'task_signing_formats', new=noop_sync)
    mocker.patch.object(script, 'get_token', new=noop_async)
    mocker.patch.object(script, 'build_filelist_dict', new=fake_filelist_dict)
    mocker.patch.object(script, 'copy_to_dir', new=noop_sync)
    mocker.patch.object(script, 'sign', new=fake_sign)
    context = mock.MagicMock()
    context.config = {'work_dir': tmpdir, 'ssl_cert': None, 'artifact_dir': tmpdir}
    await script.async_main(context)


def test_craft_aiohttp_connector():
    context = Context()
    context.config = {}
    connector = script._craft_aiohttp_connector(context)
    assert connector._ssl_context is None

    context.config['ssl_cert'] = SSL_CERT
    connector = script._craft_aiohttp_connector(context)
    assert connector._ssl_context


def test_get_default_config():
    parent_dir = os.path.dirname(os.getcwd())
    c = script.get_default_config()
    assert c['work_dir'] == os.path.join(parent_dir, 'work_dir')


def test_main(monkeypatch):
    sync_main_mock = MagicMock()
    monkeypatch.setattr(scriptworker.client, 'sync_main', sync_main_mock)
    script.main()
    sync_main_mock.asset_called_once_with(script.async_main, default_config=script.get_default_config())
