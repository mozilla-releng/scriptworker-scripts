import os
from unittest.mock import MagicMock

import mock
import pytest
import scriptworker.client
from conftest import BASE_DIR, noop_sync

import signingscript.script as script

# helper constants, fixtures, functions {{{1
EXAMPLE_CONFIG = os.path.join(BASE_DIR, "config_example.json")


# async_main {{{1
async def async_main_helper(tmpdir, mocker, formats, extra_config={}, server_type="signing_server", use_comment=None):
    def fake_filelist_dict(*args, **kwargs):
        ret = {"path1": {"full_path": "full_path1", "formats": formats}}
        if use_comment:
            ret = {"path1": {"full_path": "full_path1", "formats": formats, "comment": "Some authenticode comment"}}
        return ret

    async def fake_sign(_, val, *args, authenticode_comment=None):
        if not use_comment:
            assert authenticode_comment is None
        else:
            assert authenticode_comment == "Some authenticode comment"
        return [val]

    mocker.patch.object(script, "load_autograph_configs", new=noop_sync)
    # mocker.patch.object(script, "task_cert_type", new=noop_sync)
    mocker.patch.object(script, "task_signing_formats", return_value=formats)
    mocker.patch.object(script, "build_filelist_dict", new=fake_filelist_dict)
    mocker.patch.object(script, "sign", new=fake_sign)
    context = mock.MagicMock()
    context.config = {"work_dir": tmpdir, "artifact_dir": tmpdir, "autograph_configs": {}}
    context.config.update(extra_config)
    await script.async_main(context)


@pytest.mark.asyncio
async def test_async_main_gpg(tmpdir, tmpfile, mocker):
    formats = ["gpg"]
    fake_gpg_pubkey = tmpfile
    mocked_copy_to_dir = mocker.Mock()
    mocker.patch.object(script, "copy_to_dir", new=mocked_copy_to_dir)

    await async_main_helper(tmpdir, mocker, formats, {"gpg_pubkey": fake_gpg_pubkey})
    for call in mocked_copy_to_dir.call_args_list:
        if call[1].get("target") == "public/build/KEY":
            break
    else:
        assert False, "couldn't find copy_to_dir call that created KEY"


@pytest.mark.asyncio
async def test_async_main_gpg_no_pubkey_defined(tmpdir, mocker):
    formats = ["gpg"]

    try:
        await async_main_helper(tmpdir, mocker, formats)
    except Exception as e:
        assert e.args[0] == "GPG format is enabled but gpg_pubkey is not defined"


@pytest.mark.asyncio
async def test_async_main_gpg_pubkey_doesnt_exist(tmpdir, mocker):
    formats = ["gpg"]

    try:
        await async_main_helper(tmpdir, mocker, formats, {"gpg_pubkey": "faaaaaaake"})
    except Exception as e:
        assert e.args[0] == "gpg_pubkey (faaaaaaake) doesn't exist!"


@pytest.mark.asyncio
async def test_async_main_multiple_formats(tmpdir, mocker):
    formats = ["mar", "jar"]
    mocker.patch.object(script, "copy_to_dir", new=noop_sync)
    await async_main_helper(tmpdir, mocker, formats)


@pytest.mark.asyncio
async def test_async_main_autograph(tmpdir, mocker):
    formats = ["autograph_mar"]
    mocker.patch.object(script, "copy_to_dir", new=noop_sync)
    await async_main_helper(tmpdir, mocker, formats, {})


@pytest.mark.asyncio
@pytest.mark.parametrize("use_comment", (True, False))
async def test_async_main_autograph_authenticode(tmpdir, mocker, use_comment):
    formats = ["autograph_authenticode"]
    mocker.patch.object(script, "copy_to_dir", new=noop_sync)
    await async_main_helper(tmpdir, mocker, formats, {}, "autograph", use_comment=use_comment)


def test_get_default_config():
    parent_dir = os.path.dirname(os.getcwd())
    c = script.get_default_config()
    assert c["work_dir"] == os.path.join(parent_dir, "work_dir")


def test_main(monkeypatch):
    sync_main_mock = MagicMock()
    monkeypatch.setattr(scriptworker.client, "sync_main", sync_main_mock)
    script.main()
    sync_main_mock.asset_called_once_with(script.async_main, default_config=script.get_default_config())


@pytest.mark.asyncio
async def test_async_main_widevine_no_cert_defined(tmpdir, mocker):
    formats = ["autograph_widevine"]
    with pytest.raises(Exception) as e:
        await async_main_helper(tmpdir, mocker, formats)
        assert e.args[0] == "Widevine format is enabled, but widevine_cert is not defined"


@pytest.mark.asyncio
async def test_async_main_widevine(tmp_path, mocker):
    mocker.patch.object(script, "copy_to_dir")
    tmp_cert = tmp_path / "widevine.crt"
    formats = ["autograph_widevine"]
    await async_main_helper(tmp_path, mocker, formats, {"widevine_cert": tmp_cert})
