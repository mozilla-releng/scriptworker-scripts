import mock
import pytest

import scriptworker.client
from signingscript.test import noop_async, noop_sync, tmpdir
import signingscript.script as script

assert tmpdir  # silence flake8


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
