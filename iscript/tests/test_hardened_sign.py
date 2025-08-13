#!/usr/bin/env python
# coding=utf-8

import itertools
import os
from pathlib import Path
from shutil import copy2

import pytest

import iscript.hardened_sign as hs
from iscript.exceptions import IScriptError
from scriptworker_client.utils import makedirs

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


async def noop_async(*args, **kwargs):
    pass


def noop_sync(*args, **kwargs):
    pass


async def fail_async(*args, **kwargs):
    raise IScriptError("fail_async exception")


def symlink_upstream(config, task):
    data_dir = Path(__file__).parent / "data"
    work_dir = config["work_dir"]
    for artifact in task["payload"]["upstreamArtifacts"]:
        upstream_dir = Path(work_dir) / "cot" / artifact["taskId"]
        if not artifact.get("formats"):
            # for path in artifact["paths"]:
            #     (upstream_dir / path).touch()
            continue
        for path in artifact["paths"]:
            filename = path.split("/")[-1]
            makedirs((upstream_dir / path).parent)
            copy2(data_dir / filename, upstream_dir / path)
            # Path(upstream_dir / path).hardlink_to(data_dir / path)


_base_hs = {"deep": True, "runtime": True, "force": True, "globs": ["/"]}
hs_config = [{**_base_hs, "entitlements": "https://foo.bar", "libconstraints": "https://foo.bar/libconstraints"}]
hs_config_no_libconstraints = [{**_base_hs, "entitlements": "https://foo.bar"}]
hs_config_upstream = [{**_base_hs, "entitlements": "public/build/entitlements.xml", "libconstraints": "public/build/libconstraints.xml"}]
hs_config_mixed = [{**_base_hs, "entitlements": "https://foo.bar", "libconstraints": "public/build/libconstraints.xml"}]


@pytest.mark.asyncio
async def test_download_signing_resources(mocker):
    mocker.patch.object(hs, "retry_async", new=noop_async)
    await hs.download_signing_resources(hs_config, Path("fakefolder"))


@pytest.mark.parametrize(
    "entitlements,libconstraints",
    list(
        itertools.product(
            ["public/build/entitlements.xml", "https://moz.c/public/build/entitlements.xml"],  # entitlements
            ["public/build/libconstraints.xml", "https://moz.c/public/build/libconstraints.xml"],  # libconstraints
        )
    ),
)
def test_get_upstream_signing_resources(tmpdir, entitlements, libconstraints):
    task_id = "task1"
    for path in ["public/build/entitlements.xml", "public/build/libconstraints.xml"]:
        target_path = Path(tmpdir) / "cot" / task_id / path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.touch()
    # Test with more than one record
    cfg = [{"entitlements": entitlements, "libconstraints": libconstraints}, {"entitlements": entitlements, "libconstraints": libconstraints}]
    resources = hs.get_upstream_signing_resources(cfg, task_id, tmpdir)
    # Should only return resources that are not url
    assert len(resources) == sum(not e.startswith("https://") for e in (entitlements, libconstraints))
    for key, path in resources.items():
        assert path.exists()
        assert key in [entitlements, libconstraints]


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
    file_map = {hs_config[0]["entitlements"]: "entitlements-filename.xml", hs_config[0]["libconstraints"]: "libconstraints-filename.xml"}
    hs.build_sign_command(tmpdir, "12345identity", "keychainpath", hs_config[0], file_map)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "create_pkg,provision_profile,hardened_sign_config",
    (
        (False, None, hs_config),
        (True, None, hs_config),
        (False, {"profile_name": "comexamplehelloworld.provisionprofile", "target_path": "/Contents/embedded.provisionprofile"}, hs_config),
        (True, {"profile_name": "comexamplehelloworld.provisionprofile", "target_path": "/Contents/embedded.provisionprofile"}, hs_config),
        (False, None, hs_config_no_libconstraints),
        (True, None, hs_config_no_libconstraints),
        (False, {"profile_name": "comexamplehelloworld.provisionprofile", "target_path": "/Contents/embedded.provisionprofile"}, hs_config_no_libconstraints),
        (True, {"profile_name": "comexamplehelloworld.provisionprofile", "target_path": "/Contents/embedded.provisionprofile"}, hs_config_no_libconstraints),
        (False, None, hs_config_upstream),
        (True, None, hs_config_upstream),
        (False, {"profile_name": "comexamplehelloworld.provisionprofile", "target_path": "/Contents/embedded.provisionprofile"}, hs_config_upstream),
        (True, {"profile_name": "comexamplehelloworld.provisionprofile", "target_path": "/Contents/embedded.provisionprofile"}, hs_config_upstream),
        (False, None, hs_config_mixed),
        (True, None, hs_config_mixed),
        (False, {"profile_name": "comexamplehelloworld.provisionprofile", "target_path": "/Contents/embedded.provisionprofile"}, hs_config_mixed),
        (True, {"profile_name": "comexamplehelloworld.provisionprofile", "target_path": "/Contents/embedded.provisionprofile"}, hs_config_mixed),
    ),
)
async def test_sign_hardened_behavior(mocker, tmpdir, create_pkg, provision_profile, hardened_sign_config):
    artifact_dir = os.path.join(str(tmpdir), "artifact")
    work_dir = os.path.join(str(tmpdir), "work")
    makedirs(artifact_dir)
    makedirs(work_dir)
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
                {"taskId": "task1", "paths": ["public/build/example.tar.gz"], "formats": ["macapp"]},
                {"taskId": "task2", "paths": ["public/build/entitlements.xml", "public/build/libconstraints.xml"], "formats": []},
            ],
            "behavior": "mac_sign_hardened",
            "hardened-sign-config": hardened_sign_config,
        },
    }
    symlink_upstream(config, task)
    if provision_profile is not None:
        task["payload"]["provisioning-profile-config"] = [provision_profile]
        pprofile_dir = os.path.join(str(tmpdir), "provisionprofiles")
        makedirs(pprofile_dir)
        with open(os.path.join(pprofile_dir, provision_profile["profile_name"]), "w"):
            pass

    def mock_get_upstream_signing_resources(*_):
        res = {hardened_sign_config[0]["entitlements"]: "public/build/entitlements.xml"}
        if libconstraints := hardened_sign_config[0].get("libconstraints", None):
            res[libconstraints] = "public/build/libconstraints.xml"
        return res

    async def mock_download_signing_resources(*_):
        return mock_get_upstream_signing_resources(None, None, None)

    orig_run_command = hs.run_command

    async def mock_run_command(cmd, **kwargs):
        if cmd[0] != "codesign":
            return orig_run_command(cmd, **kwargs)

        # Verify the codesign arguments
        assert "--sign" in cmd
        assert "--keychain" in cmd
        assert "--entitlements" in cmd
        pass

    mocker.patch.object(hs, "download_signing_resources", new=mock_download_signing_resources)
    # These functions return the exact same type of data
    mocker.patch.object(hs, "get_upstream_signing_resources", new=mock_get_upstream_signing_resources)
    mocker.patch.object(hs, "unlock_keychain", new=noop_async)
    mocker.patch.object(hs, "update_keychain_search_path", new=noop_async)
    mocker.patch.object(hs, "get_sign_config", return_value=config["mac_config"]["dep"])
    mocker.patch.object(hs, "run_command", new=mock_run_command)

    async def mock_create_pkg_files(config, sign_config, apps, requirements_plist_path):
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        for app in apps:
            hs.set_app_path_and_name(app)

            # Check that the provisioning profile was copied into the bundle
            if provision_profile is not None:
                filename = os.path.join(app.app_path, provision_profile["target_path"].strip("/"))
                assert os.path.isfile(filename)

            app.pkg_path = app.app_path.replace(".app", ".pkg")
            copy2(os.path.join(data_dir, "example.pkg"), app.pkg_path)

    if create_pkg:
        mocker.patch.object(hs, "download_requirements_plist_file", return_value=os.path.join(work_dir, "requirements.plist"))
        mocker.patch.object(hs, "create_pkg_files", new=mock_create_pkg_files)
    else:
        mocker.patch.object(hs, "download_requirements_plist_file", new=fail_async)
        mocker.patch.object(hs, "create_pkg_files", new=fail_async)
        mocker.patch.object(hs, "copy_pkgs_to_artifact_dir", new=fail_async)

    await hs.sign_hardened_behavior(config, task, create_pkg=create_pkg)

    # The output artifacts should be created
    assert os.path.isfile(os.path.join(artifact_dir, "public", "build", "example.tar.gz"))
    if create_pkg:
        assert os.path.isfile(os.path.join(artifact_dir, "public", "build", "example.pkg"))
