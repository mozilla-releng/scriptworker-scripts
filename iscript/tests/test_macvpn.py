#!/usr/bin/env python
# coding=utf-8
"""Test iscript.mac
"""
import os

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
async def test_sign_app(mocker):
    mocker.patch.object(macvpn, "download_entitlements_file", new=noop_async)
    mocker.patch.object(macvpn, "download_provisioning_profile", new=noop_async)
    mocker.patch.object(macvpn, "sign_all_apps", new=noop_async)
    app = App(app_name="mock.app")
    await macvpn._sign_app({}, {}, app, "", "")


@pytest.mark.asyncio
async def test_notarize_vpn_behavior(mocker):
    def get_app_paths(config, task):
        return [App(parent_dir=".")]

    def get_sign_config(*args, **kwargs):
        return {"signing_keychain": None, "keychain_password": None}

    mocker.patch.object(macvpn, "_sign_app", new=noop_async)
    mocker.patch.object(macvpn, "_create_notarization_zipfile", new=noop_async)
    mocker.patch.object(macvpn, "get_app_paths", new=get_app_paths)
    mocker.patch.object(macvpn, "extract_all_apps", new=noop_async)
    mocker.patch.object(macvpn, "run_command", new=noop_async)
    mocker.patch.object(macvpn.os, "remove", new=noop_sync)
    mocker.patch.object(macvpn.os, "remove", new=noop_sync)
    mocker.patch.object(macvpn, "get_sign_config", new=get_sign_config)
    mocker.patch.object(macvpn, "unlock_keychain", new=noop_async)
    mocker.patch.object(macvpn, "update_keychain_search_path", new=noop_async)
    mocker.patch.object(macvpn, "_sign_app", new=noop_async)
    mocker.patch.object(macvpn, "create_pkg_files", new=noop_async)
    mocker.patch.object(macvpn, "_create_notarization_zipfile", new=noop_async)
    mocker.patch.object(macvpn, "notarize_no_sudo", new=noop_async)
    mocker.patch.object(macvpn, "poll_all_notarization_status", new=noop_async)
    mocker.patch.object(macvpn, "staple_notarization", new=noop_async)
    mocker.patch.object(macvpn, "copy_pkgs_to_artifact_dir", new=noop_async)

    task = {
        "payload": {
            "upstreamArtifacts": [{"formats": ["mac_behavior"]}],
            "loginitems-entitlements-url": "",
            "nativemessaging-entitlements-url": "",
            "entitlements-url": "",
        }
    }
    config = {"work_dir": ""}
    await macvpn.notarize_vpn_behavior(config, task)
