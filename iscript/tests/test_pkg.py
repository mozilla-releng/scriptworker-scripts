#!/usr/bin/env python
# coding=utf-8
"""Test iscript.pkg"""
import os
import plistlib
import pytest

from shutil import copy2
from scriptworker_client.utils import makedirs

import iscript.pkg as pkg

# helpers {{{1
async def noop_async(*args, **kwargs):
    pass


def symlink_upstream(config, task):
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    work_dir = config["work_dir"]
    for artifact in task["payload"]["upstreamArtifacts"]:
        upstream_dir = os.path.join(work_dir, "cot", artifact["taskId"], "public", "build")
        makedirs(os.path.dirname(upstream_dir))
        os.symlink(data_dir, upstream_dir)


# sign_pkg_behavior {{{1
@pytest.mark.asyncio
async def test_sign_pkg_behavior(mocker, tmpdir):
    artifact_dir = os.path.join(str(tmpdir), "artifact")
    work_dir = os.path.join(str(tmpdir), "work")
    config = {
        "artifact_dir": artifact_dir,
        "work_dir": work_dir,
        "local_notarization_accounts": ["acct0", "acct1", "acct2"],
        "mac_config": {
            "dep": {
                "designated_requirements": "",  # put this here bc it's easier
                "zipfile_cmd": "zip",
                "notarize_type": "single_zip",
                "signing_keychain": "keychain_path",
                "sign_with_entitlements": False,
                "base_bundle_id": "org.test",
                "identity": "id",
                "keychain_password": "keychain_password",
                "pkg_cert_id": "cert_id",
                "apple_notarization_account": "apple_account",
                "apple_notarization_password": "apple_password",
                "apple_asc_provider": "apple_asc_provider",
                "notarization_poll_timeout": 2,
                "create_pkg": True,
            }
        },
    }
    task = {
        "scopes": [
            "project:releng:signing:cert:dep-signing",
        ],
        "payload": {
            "upstreamArtifacts": [
                {"taskId": "task-identifer", "paths": ["public/build/example.tar.gz", "public/build/example.pkg"], "formats": []},
            ]
        },
    }
    symlink_upstream(config, task)

    async def mock_run_command(cmd, **kwargs):
        # Verify that the productsign command was run, with signing arguments.
        assert cmd[0] == "productsign"
        assert "--keychain" in cmd
        assert "--sign" in cmd

        # Verify that we are signing a pkg file
        assert os.path.basename(cmd[-2]) == "example.pkg"
        assert os.path.basename(cmd[-1]) == "example.pkg"
        assert "productsign" in os.path.dirname(cmd[-1])

        # Don't actually sign - just copy
        copy2(cmd[-2], cmd[-1])

    mocker.patch.object(pkg, "run_command", new=mock_run_command)
    mocker.patch.object(pkg, "unlock_keychain", new=noop_async)
    mocker.patch.object(pkg, "update_keychain_search_path", new=noop_async)
    mocker.patch.object(pkg, "get_sign_config", return_value=config["mac_config"]["dep"])

    await pkg.sign_pkg_behavior(config, task)

    # The "signed" package should exist in the artifact dir.
    assert os.path.isfile(os.path.join(artifact_dir, "public", "build", "example.pkg"))
