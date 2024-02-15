#!/usr/bin/env python
# coding=utf-8

from pathlib import Path
import os
import pytest
import copy

import iscript.hardened_sign as hs
from iscript.exceptions import IScriptError

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


async def noop_async(*args, **kwargs):
    pass


def noop_sync(*args, **kwargs):
    pass


async def fail_async(*args, **kwargs):
    raise IScriptError("fail_async exception")


hs_config = [{"deep": True, "runtime": True, "force": True, "entitlements": "https://foo.bar", "globs": ["/"]}]


@pytest.mark.asyncio
async def test_download_signing_resources(mocker):
    mocker.patch.object(hs, "retry_async", new=noop_async)
    await hs.download_signing_resources(hs_config, Path("fakefolder"))


def test_check_globs():
    globs = ["doesntexist/*", "/*"]
    hs.check_globs(TEST_DATA_DIR, globs)


def test_copy_provisioning_profile(tmpdir):
    pprofile = {"profile_name": "test.profile", "target_path": "/test.profile"}
    # Source pprofile
    sourcedir = os.path.join(tmpdir, "provisionprofiles")
    os.mkdir(sourcedir)
    source_profile = Path(sourcedir) / pprofile["profile_name"]
    source_profile.touch()
    config = {"work_dir": os.path.join(tmpdir, "foo")}
    hs.copy_provisioning_profile(pprofile, tmpdir, config)
    assert (Path(tmpdir) / pprofile["profile_name"]).exists()


def test_copy_provisioning_profile_fail(tmpdir):
    pprofile = {"profile_name": "test.profile", "target_path": "/"}
    config = {"work_dir": os.path.join(tmpdir, "foo")}
    sourcedir = os.path.join(tmpdir, "provisionprofiles")
    os.mkdir(sourcedir)

    # Source file doesn't exist
    with pytest.raises(IScriptError):
        hs.copy_provisioning_profile(pprofile, tmpdir, config)

    # Illegal source traversal
    pprofile = {"profile_name": "../test.profile", "target_path": "/"}
    source_profile = Path(sourcedir) / pprofile["profile_name"]
    source_profile.touch()
    with pytest.raises(IScriptError):
        hs.copy_provisioning_profile(pprofile, tmpdir, config)

    # Illegal destination traversal
    pprofile = {"profile_name": "test.profile", "target_path": "../../../"}
    sourcedir = os.path.join(tmpdir, "provisionprofiles")
    source_profile = Path(sourcedir) / pprofile["profile_name"]
    source_profile.touch()
    with pytest.raises(IScriptError):
        hs.copy_provisioning_profile(pprofile, tmpdir, config)


def test_build_sign_command(tmpdir):
    file_map = {hs_config[0]["entitlements"]: "filepath"}
    hs.build_sign_command(tmpdir, "12345identity", "keychainpath", hs_config[0], file_map)
