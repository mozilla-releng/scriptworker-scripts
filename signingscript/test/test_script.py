import json
import mock
import os
import pytest
import sys

import scriptworker.client
from scriptworker.exceptions import ScriptWorkerTaskException
from signingscript.test import event_loop, noop_async, noop_sync, read_file, tmpdir
import signingscript.script as script

assert event_loop or tmpdir  # silence flake8

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
EXAMPLE_CONFIG = os.path.join(BASE_DIR, 'config_example.json')
SSL_CERT = os.path.join(BASE_DIR, "signingscript", "data", "host.cert")


# helper functions {{{1
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


# SigningContext {{{1
def test_signing_context():
    c = script.SigningContext()
    c.write_json()


# async_main {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize('formats', (['gpg'], ['mar', 'jar']))
async def test_async_main(tmpdir, mocker, formats):

    def fake_filelist_dict(*args, **kwargs):
        return {'path1': {'full_path': 'full_path1', 'formats': formats}}

    mocker.patch.object(scriptworker.client, 'get_task', new=noop_sync)
    mocker.patch.object(script, 'validate_task_schema', new=noop_sync)
    mocker.patch.object(script, 'load_signing_server_config', new=noop_sync)
    mocker.patch.object(script, 'task_cert_type', new=noop_sync)
    mocker.patch.object(script, 'task_signing_formats', new=noop_sync)
    mocker.patch.object(script, 'get_token', new=noop_async)
    mocker.patch.object(script, 'build_filelist_dict', new=fake_filelist_dict)
    mocker.patch.object(script, 'copy_to_dir', new=noop_sync)
    mocker.patch.object(script, 'sign_file', new=noop_async)
    context = mock.MagicMock()
    context.config = {'work_dir': tmpdir, 'ssl_cert': None, 'artifact_dir': tmpdir}
    await script.async_main(context)


# get_default_config {{{1
def test_get_default_config():
    parent_dir = os.path.dirname(os.getcwd())
    c = script.get_default_config()
    assert c['work_dir'] == os.path.join(parent_dir, 'work_dir')


# usage {{{1
def test_usage():
    with pytest.raises(SystemExit):
        script.usage()


# main {{{1
def test_main_missing_args(mocker):
    mocker.patch.object(sys, 'argv', new=[__file__])
    with pytest.raises(SystemExit):
        script.main()


def test_main_argv(tmpdir, mocker, event_loop):
    conf_file = get_conf_file(tmpdir, verbose=False, ssl_cert=None)
    mocker.patch.object(sys, 'argv', new=[__file__, conf_file])
    mocker.patch.object(script, 'async_main', new=noop_async)
    script.main()


def test_main_noargv(tmpdir, mocker, event_loop):
    conf_file = get_conf_file(tmpdir, verbose=True, ssl_cert=SSL_CERT)
    mocker.patch.object(script, 'async_main', new=die_async)
    with pytest.raises(SystemExit):
        script.main(config_path=conf_file)
