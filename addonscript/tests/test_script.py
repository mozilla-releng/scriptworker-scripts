import os
from unittest import mock

from aiohttp.client_exceptions import ClientConnectionError
import pytest
import scriptworker.utils

import addonscript.script as script
from addonscript.exceptions import AMOConflictError, SignatureError


@pytest.mark.asyncio
async def test_sign_addon(context, mocker, tmpdir):
    context.config["artifact_dir"] = tmpdir
    mocker.patch.object(scriptworker.utils, "_define_sleep_time", return_value=0)
    mocker.patch.object(script, "do_upload", side_effect=[ClientConnectionError(), {"uuid": "uuid"}])
    mocker.patch.object(script, "check_upload", side_effect=[SignatureError(), ClientConnectionError(), None])
    mocker.patch.object(script, "do_create_version", side_effect=[ClientConnectionError(), {"id": 1234}])
    mocker.patch.object(script, "get_signed_addon_info", side_effect=[SignatureError(), ("http://download/this/en-GB.xpi", 1, "sha256")])
    mocker.patch.object(script, "get_signed_xpi", side_effect=[SignatureError(), None])

    await script.sign_addon(context, "en-GB")


@pytest.mark.asyncio
async def test_sign_addon_conflict(context, mocker, tmpdir):
    context.config["artifact_dir"] = tmpdir
    mocker.patch.object(scriptworker.utils, "_define_sleep_time", return_value=0)
    mocker.patch.object(script, "do_upload", side_effect=[ClientConnectionError(), {"uuid": "uuid"}])
    mocker.patch.object(script, "check_upload", side_effect=[SignatureError(), ClientConnectionError(), None])
    mocker.patch.object(script, "do_create_version", side_effect=[ClientConnectionError(), AMOConflictError("")])
    mocker.patch.object(script, "get_signed_addon_info", side_effect=[SignatureError(), ("http://download/this/en-GB.xpi", 1, "sha256")])
    mocker.patch.object(script, "get_signed_xpi", side_effect=[SignatureError(), None])

    await script.sign_addon(context, "en-GB")


def test_build_locales_context(context, mocker):

    def mock_get_langpack_info(filename):
        locale = os.path.splitext(filename)[0]
        return {
            "id": f"langpack-{locale}@firefox.mozilla.org",
            "locale": os.path.splitext(filename)[0],
            "version": "110.0buildid20230224110500",
            "unsigned": filename,
            "min_version": "110.0",
        }

    mocker.patch.object(script, "get_langpack_info", side_effect=mock_get_langpack_info)
    mocker.patch.object(script, "build_filelist", return_value=["en-US.xpi", "fr.xpi"])

    script.build_locales_context(context)
    assert list(context.locales) == ["en-US", "fr"]
    for l in context.locales:
        assert set(context.locales[l]) >= {"id", "min_version", "unsigned", "version"}
