#!/usr/bin/env python
# coding=utf-8
"""Test iscript.mac"""
import os
import plistlib
import pytest

import iscript.macvpn as macvpn
from iscript.exceptions import IScriptError
from iscript.mac import App


async def noop_async(*args, **kwargs):
    pass


def noop_sync(*args, **kwargs):
    pass


async def fail_async(*args, **kwargs):
    raise IScriptError("fail_async exception")


@pytest.mark.asyncio
async def test_create_notarization_zipfile(mocker):
    mocker.patch.object(macvpn, "run_command", new=noop_async)
    await macvpn._create_notarization_zipfile("workdir", "source", "dest")


@pytest.mark.asyncio
async def test_codesign(mocker):
    mocker.patch.object(macvpn, "run_command", new=noop_async)
    sign_config = {"identity": "1", "signing_keychain": "1"}
    await macvpn._codesign(sign_config, "fake/path")


@pytest.mark.asyncio
async def test_create_pkg_plist(mocker, tmp_path):
    async def _pkgbuild_analyze_async(cmd, **kwargs):
        outfile = cmd[-1]
        testplist = [{"BundleIsRelocatable": True, "BundleHasStrictIdentifier": True, "BundleIsVersionChecked": True}]
        with open(outfile, "wb") as fp:
            plistlib.dump(testplist, fp)

    mocker.patch.object(macvpn, "run_command", new=_pkgbuild_analyze_async)

    app = App(app_name="mock.app", parent_dir=os.path.join(tmp_path, "Applications"))
    plist_path = os.path.join(tmp_path, "component.plist")

    await macvpn._create_pkg_plist(tmp_path, plist_path, BundleIsRelocatable=False)
    with open(plist_path, "rb") as fp:
        x = plistlib.load(fp)
        assert len(x) == 1
        assert x[0]["BundleIsRelocatable"] == False


@pytest.mark.asyncio
async def test_create_pkg_files(mocker, tmp_path):
    mocker.patch.object(macvpn, "run_command", new=noop_async)
    mocker.patch.object(macvpn, "copytree", new=noop_sync)
    mocker.patch.object(macvpn, "copy2", new=noop_sync)
    mocker.patch.object(macvpn.os, "remove", new=noop_sync)
    mocker.patch.object(macvpn.os, "mkdir", new=noop_sync)
    mocker.patch.object(macvpn, "_create_pkg_plist", new=noop_async)

    config = {"work_dir": tmp_path}
    sign_config = {"signing_keychain": "1", "base_bundle_id": "1"}
    app = App(app_name="mock.app", parent_dir=tmp_path)
    await macvpn._create_pkg_files(config, sign_config, app)
    sign_config = {"pkg_cert_id": "1", "signing_keychain": "1", "base_bundle_id": "1"}
    await macvpn._create_pkg_files(config, sign_config, app)


@pytest.mark.asyncio
async def test_sign_app(mocker, tmp_path):
    mocker.patch.object(macvpn, "download_entitlements_file", new=noop_async)
    mocker.patch.object(macvpn, "sign_all_apps", new=noop_async)
    app = App(app_name="mock.app")
    sign_config = {"provisioning_profile_dir": str(tmp_path)}
    await macvpn._sign_app({}, {}, app, "", None)
    fake_file = tmp_path / "fake.provisionprofile"
    fake_file.write_text("contents")
    # Missing dir
    await macvpn._sign_app({"work_dir": "."}, {}, app, "", "Does not exist")
    # Missing file
    await macvpn._sign_app({"work_dir": "."}, sign_config, app, "", "Does not exist")
    # With both dir and file
    await macvpn._sign_app({"work_dir": "."}, sign_config, app, "", str(fake_file))


@pytest.mark.asyncio
async def test_vpn_behavior(mocker):
    def get_app_paths(config, task):
        return [App(parent_dir=".")]

    def get_sign_config(*args, **kwargs):
        return {"signing_keychain": None, "keychain_password": None, "pkg_cert_id": "123"}

    mocker.patch.object(macvpn, "_sign_app", new=noop_async)
    mocker.patch.object(macvpn, "get_app_paths", new=get_app_paths)
    mocker.patch.object(macvpn, "extract_all_apps", new=noop_async)
    mocker.patch.object(macvpn, "run_command", new=noop_async)
    mocker.patch.object(macvpn.os, "remove", new=noop_sync)
    mocker.patch.object(macvpn, "get_sign_config", new=get_sign_config)
    mocker.patch.object(macvpn, "unlock_keychain", new=noop_async)
    mocker.patch.object(macvpn, "update_keychain_search_path", new=noop_async)
    mocker.patch.object(macvpn, "_sign_app", new=noop_async)
    mocker.patch.object(macvpn, "_create_pkg_files", new=noop_async)
    mocker.patch.object(macvpn, "_codesign", new=noop_async)
    mocker.patch.object(macvpn, "copy_pkgs_to_artifact_dir", new=noop_async)
    # We should call the legacy signer if no config was provided.
    mocker.patch.object(macvpn, "sign_hardened_behavior", new=fail_async)

    task = {
        "payload": {
            "upstreamArtifacts": [{"formats": ["mac_behavior"]}],
            "loginItemsEntitlementsUrl": "http://localhost/notarealurl",
            "loginItemsProvisioningProfileUrl": "http://localhost/notarealurl",
            "nativeMessagingEntitlementsUrl": "http://localhost/notarealurl",
            "nativeMessagingProvisioningProfileUrl": "http://localhost/notarealurl",
            "entitlementsUrl": "http://localhost/notarealurl",
            "provisioningProfileUrl": "http://localhost/notarealurl",
        }
    }
    config = {"work_dir": ""}
    await macvpn.vpn_behavior(config, task)


@pytest.mark.asyncio
async def test_vpn_hardened(mocker):
    def get_app_paths(config, task):
        return [App(parent_dir=".")]

    def get_sign_config(*args, **kwargs):
        return {"signing_keychain": None, "keychain_password": None, "pkg_cert_id": "123"}

    async def mock_sign_app(config, task, create_pkg):
        return get_app_paths(config, task)

    mocker.patch.object(macvpn, "get_app_paths", new=get_app_paths)
    mocker.patch.object(macvpn, "get_sign_config", new=get_sign_config)
    mocker.patch.object(macvpn, "_create_pkg_files", new=noop_async)
    mocker.patch.object(macvpn, "copy_pkgs_to_artifact_dir", new=noop_async)
    # We should call the hardened signer if config was provided.
    mocker.patch.object(macvpn, "sign_hardened_behavior", new=mock_sign_app)
    mocker.patch.object(macvpn, "vpn_legacy_behavior", new=fail_async)

    task = {
        "payload": {
            "behavior": "mac_sign_and_pkg_vpn",
            "hardened-sign-config": [{"deep": False, "entitlements": "http://localhost/notarealurl", "force": False, "globs": "/", "runtime": True}],
            "provisioning-profile-config": [
                {
                    "profile_name": "comexamplemacosFirefoxVPN.provisionprofile",
                    "target_path": "/Contents/embedded.provisionprofile",
                }
            ],
            "upstreamArtifacts": [{"formats": ["macapp"]}],
        }
    }
    config = {"work_dir": ""}

    await macvpn.vpn_behavior(config, task)
