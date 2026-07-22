#!/usr/bin/env python
# coding=utf-8
"""Test iscript.mac"""
import asyncio
import os
import plistlib
from functools import partial
from shutil import copy2

import pexpect
import pytest
from scriptworker_client.aio import retry_async
from scriptworker_client.utils import makedirs

import iscript.mac as mac
from iscript.exceptions import IScriptError, TimeoutError, UnknownAppDir

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


# helpers {{{1
async def noop_async(*args, **kwargs):
    pass


def noop_sync(*args, **kwargs):
    pass


async def fail_async(*args, **kwargs):
    raise IScriptError("fail_async exception")


def touch(path):
    parent_dir = os.path.dirname(path)
    makedirs(parent_dir)
    with open(path, "w"):
        pass


# App {{{1
def test_app():
    """``App`` attributes can be set, and ``check_required_attrs`` raises if
    the required attrs aren't set.

    """
    a = mac.App()
    assert a.orig_path == ""
    a.orig_path = "foo"
    assert a.orig_path == "foo"
    a.check_required_attrs(["orig_path"])
    with pytest.raises(IScriptError):
        a.check_required_attrs(["app_path"])


# tar helpers {{{1
@pytest.mark.parametrize(
    "path, expected, raises", (("foo/bar/target.tar.gz", "czf", False), ("foo/bar/target.tar.bz2", "cjf", False), ("foo/bar/target.tar.xz", None, True))
)
def test_get_tar_create_options(path, expected, raises):
    if raises:
        with pytest.raises(IScriptError):
            mac._get_tar_create_options(path)
    else:
        assert mac._get_tar_create_options(path) == expected


@pytest.mark.parametrize(
    "path, expected, raises",
    (("foo/bar/target.tar.gz", "foo/bar/target.pkg", False), ("foo/bar/target.tar.bz2", "foo/bar/target.pkg", False), ("foo/bar/target.tar.xz", None, True)),
)
def test_get_pkg_name_from_tarball(path, expected, raises):
    if raises:
        with pytest.raises(IScriptError):
            mac._get_pkg_name_from_tarball(path)
    else:
        assert mac._get_pkg_name_from_tarball(path) == expected


# set_app_path_and_name {{{1
def test_app_path_and_name(mocker):
    """``app_path_and_name`` sets the ``app_path`` and ``app_name`` if not
    already set.

    """

    def fake_get_app_dir(parent_dir):
        x = os.path.basename(parent_dir)
        return os.path.join(parent_dir, "{}.app".format(x))

    all_paths = [
        mac.App(parent_dir="foo/1"),
        mac.App(parent_dir="foo/2", app_path="foo/2/2.app"),
        mac.App(parent_dir="foo/3", app_path="foo/4/4.app", app_name="4.app"),
    ]
    mocker.patch.object(mac, "get_app_dir", new=fake_get_app_dir)
    expected = [["foo/1/1.app", "1.app"], ["foo/2/2.app", "2.app"], ["foo/4/4.app", "4.app"]]
    for app in all_paths:
        mac.set_app_path_and_name(app)
        assert [app.app_path, app.app_name] == expected.pop(0)


# get_bundle_executable {{{1
def test_get_bundle_executable(tmpdir):
    """``get_bundle_executable`` returns the CFBundleExecutable."""
    os.mkdir(os.path.join(tmpdir, "Contents"))
    with open(os.path.join(tmpdir, "Contents", "Info.plist"), "wb") as fp:
        plistlib.dump({"CFBundleExecutable": "main"}, fp)

    assert mac.get_bundle_executable(tmpdir) == "main"


# sign_single_files {{{1
@pytest.mark.parametrize("exists, filename", ((True, "geckodriver.tar.gz"), (False, "geckodriver.tar.gz"), (True, "openh264.zip")))
@pytest.mark.asyncio
async def test_sign_single_files(exists, filename, mocker, tmpdir):
    """Render ``sign_single_files`` noop and verify we have complete code coverage."""
    sign_config = {"identity": "id", "signing_keychain": "keychain", "designated_requirements": ""}
    config = {"artifact_dir": os.path.join(tmpdir, "artifacts")}
    app = mac.App(
        orig_path=os.path.join(tmpdir, f"cot/task1/public/build/{filename}"),
        parent_dir=os.path.join(tmpdir, "0"),
        artifact_prefix=os.path.join("public/build"),
        single_file_globs=["geckodriver"],
    )

    makedirs(app.parent_dir)
    makedirs(os.path.dirname(app.orig_path))
    copy2(os.path.join(TEST_DATA_DIR, "test.zip"), app.orig_path)
    if exists:
        touch(os.path.join(app.parent_dir, "geckodriver"))
    mocker.patch.object(mac, "run_command", new=noop_async)
    if exists:
        await mac.sign_single_files(config, sign_config, [app])
    else:
        with pytest.raises(IScriptError):
            await mac.sign_single_files(config, sign_config, [app])


# _get_sign_command{{{1
@pytest.mark.parametrize(
    "sign_config,entitlements_path",
    (
        ({"designated_requirements": "%s", "hardened_runtime_only_files": "filename"}, None),
        ({"designated_requirements": "%s", "sign_with_entitlements": True}, "entitlements/path"),
        ({"designated_requirements": "%s"}, None),
    ),
)
def test_get_sign_command(sign_config, entitlements_path):
    command = mac._get_sign_command("ident", "keychain_name", sign_config, "filename", entitlements_path=entitlements_path)
    assert len(command) > 0


# sign_app {{{1
@pytest.mark.parametrize("sign_with_entitlements,has_clearkey,skip_dirs", ((True, True, tuple()), (False, False, ("foo.app",))))
@pytest.mark.asyncio
async def test_sign_app(mocker, tmpdir, sign_with_entitlements, has_clearkey, skip_dirs):
    """Render ``sign_app`` noop and verify we have complete code coverage."""
    sign_config = {
        "identity": "id",
        "signing_keychain": "keychain",
        "sign_with_entitlements": sign_with_entitlements,
        "designated_requirements": "",
        "sign_dirs": ("MacOS", "Library"),
        "skip_dirs": skip_dirs,
    }
    entitlements_path = os.path.join(tmpdir, "entitlements")
    app_path = os.path.join(tmpdir, "foo.app")

    contents_dir = os.path.join(app_path, "Contents")
    dir1 = os.path.join(contents_dir, "MacOS")
    dir2 = os.path.join(dir1, "foo.app", "Contents", "MacOS")
    ignore_dir = os.path.join(contents_dir, "ignoreme")
    for dir_ in (dir1, dir2, ignore_dir):
        makedirs(dir_)
    for dir_ in (dir1, dir2):
        touch(os.path.join(dir_, "other"))
        touch(os.path.join(dir_, "main"))
    touch(os.path.join(contents_dir, "dont_sign"))
    if has_clearkey:
        dir_ = os.path.join(contents_dir, "Resources/gmp-clearkey/0.1")
        file_ = "libclearkey.dylib"
        makedirs(dir_)
        touch(os.path.join(dir_, file_))
    mocker.patch.object(mac, "run_command", new=noop_async)
    mocker.patch.object(mac, "get_bundle_executable", return_value="main")
    mocker.patch.object(mac, "copy2", new=noop_sync)
    await mac.sign_app(sign_config, app_path, entitlements_path, "test")


# verify_app_signature {{{1
@pytest.mark.asyncio
async def test_verify_app_signature_noop(mocker):
    """``verify_app_signature`` is noop when ``verify_mac_signature`` is False."""

    sign_config = {"verify_mac_signature": False}
    # If we actually run_command, raise to show we're doing too much
    mocker.patch.object(mac, "run_command", new=fail_async)
    await mac.verify_app_signature(sign_config, mac.App())


# unlock_keychain {{{1
def fake_spawn(val, *args, **kwargs):
    return val


@pytest.mark.parametrize("results", ([1, 0], [0]))
@pytest.mark.asyncio
async def test_unlock_keychain_successful(results, mocker):
    """Mock a successful keychain unlock."""

    async def fake_expect(*args, **kwargs):
        return results.pop(0)

    child = mocker.Mock()
    child.expect = fake_expect
    child.exitstatus = 0
    child.signalstatus = None
    mocker.patch.object(pexpect, "spawn", new=partial(fake_spawn, child))
    await mac.unlock_keychain("x", "y")


@pytest.mark.asyncio
async def test_unlock_keychain_timeout(mocker):
    """``unlock_keychain`` raises a ``TimeoutError`` on pexpect timeout."""

    async def fake_expect(*args, **kwargs):
        raise pexpect.exceptions.TIMEOUT("foo")

    child = mocker.Mock()
    child.expect = fake_expect
    child.exitstatus = 0
    child.signalstatus = None
    mocker.patch.object(pexpect, "spawn", new=partial(fake_spawn, child))
    with pytest.raises(TimeoutError):
        await mac.unlock_keychain("x", "y")


@pytest.mark.asyncio
async def test_unlock_keychain_failure(mocker):
    """``unlock_keychain`` throws an ``IScriptError`` on non-zero exit status."""
    results = [0]

    async def fake_expect(*args, **kwargs):
        return results.pop(0)

    child = mocker.Mock()
    child.expect = fake_expect
    child.exitstatus = 1
    child.signalstatus = None
    mocker.patch.object(pexpect, "spawn", new=partial(fake_spawn, child))
    with pytest.raises(IScriptError):
        await mac.unlock_keychain("x", "y")


# get_app_dir {{{1
@pytest.mark.parametrize("apps, raises", (([], True), (["foo.app"], False), (["foo.notanapp"], True), (["one.app", "two.app"], True)))
def test_get_app_dir(tmpdir, apps, raises):
    """``get_app_dir`` returns the single ``.app`` dir in ``parent_dir``, and
    raises ``UnknownAppDir`` if there is greater or fewer than one ``.app``.

    """
    for app in apps:
        os.makedirs(os.path.join(tmpdir, app))

    if raises:
        with pytest.raises(UnknownAppDir):
            mac.get_app_dir(tmpdir)
    else:
        assert mac.get_app_dir(tmpdir) == os.path.join(tmpdir, apps[0])


# get_app_paths {{{1
@pytest.mark.parametrize(
    "path, expected, raises", (("public/build/foo", "public/", False), ("releng/partner/bar", "releng/partner/", False), ("unknown/prefix/baz", None, True))
)
def test_get_artifact_prefix(path, expected, raises):
    """``_get_artifact_prefix`` returns the known prefix of the artifact path,
    or raises ``IScriptError`` if the prefix is unknown.

    """
    if raises:
        with pytest.raises(IScriptError):
            mac._get_artifact_prefix(path)
    else:
        assert mac._get_artifact_prefix(path) == expected


def test_get_app_paths():
    """``get_app_paths`` creates ``App`` objects with ``orig_path`` set to
    the cot-downloaded artifact paths.

    """
    config = {"work_dir": "work"}
    task = {
        "payload": {
            "upstreamArtifacts": [
                {"paths": ["public/foo"], "taskId": "task1", "formats": ["macapp"]},
                {"paths": ["public/bar", "public/baz"], "taskId": "task2", "formats": ["macapp"]},
            ]
        }
    }
    paths = []
    apps = mac.get_app_paths(config, task)
    for app in apps:
        assert isinstance(app, mac.App)
        paths.append(app.orig_path)
    assert paths == ["work/cot/task1/public/foo", "work/cot/task2/public/bar", "work/cot/task2/public/baz"]


# extract_all_apps {{{1
@pytest.mark.parametrize(
    "suffix, command, raises",
    (
        ("dmg", os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "iscript", "data", "unpack-diskimage"), False),
        ("tar.gz", "tar", False),
        ("tar.bz2", "tar", False),
        ("zip", "unzip", False),
        ("unknown_ext", None, True),
    ),
)
@pytest.mark.asyncio
async def test_extract_all_apps(mocker, tmpdir, suffix, command, raises):
    """``extract_all_apps`` creates ``parent_dir`` and raises if any tar command
    fails. The ``run_command`` calls all start with a commandline that calls
    ``tar``.

    """

    async def fake_run_command(*args, **kwargs):
        assert args[0][0] == command
        if raises:
            raise IScriptError("foo")

    mocker.patch.object(mac, "run_command", new=fake_run_command)
    work_dir = os.path.join(str(tmpdir), "work")
    config = {"work_dir": work_dir, "dmg_prefix": "test"}
    all_paths = [
        mac.App(orig_path=os.path.join(work_dir, f"orig1.{suffix}")),
        mac.App(orig_path=os.path.join(work_dir, f"orig2.{suffix}")),
        mac.App(orig_path=os.path.join(work_dir, f"orig3.{suffix}")),
    ]
    if raises:
        with pytest.raises(IScriptError):
            await mac.extract_all_apps(config, all_paths)
    else:
        await mac.extract_all_apps(config, all_paths)
        for i in ("0", "1", "2"):
            assert os.path.isdir(os.path.join(work_dir, i))


# sign_all_apps {{{1
@pytest.mark.parametrize("raises", (True, False))
@pytest.mark.asyncio
async def test_sign_all_apps(mocker, tmpdir, raises):
    """``sign_all_apps`` calls ``sign`` and raises on failure."""
    sign_config = {"x": "y", "signing_keychain": "keychain", "keychain_password": "password"}
    config = {}
    entitlements_path = "fake_entitlements_path"
    fake_provisioning_profile_path = "fake_provisioning_profile_path"
    work_dir = str(tmpdir)
    all_paths = []
    app_paths = []
    for i in range(3):
        app_path = "{}.app".format(str(i))
        app_paths.append(app_path)
        all_paths.append(mac.App(parent_dir=os.path.join(work_dir, str(i)), app_path=app_path))

    async def fake_sign(arg1, arg2, arg3, arg4):
        assert arg1 == sign_config
        assert arg2 in app_paths
        assert arg3 == entitlements_path
        assert arg4 == fake_provisioning_profile_path
        if raises:
            raise IScriptError("foo")

    mocker.patch.object(mac, "set_app_path_and_name", return_value=None)
    mocker.patch.object(mac, "sign_app", new=fake_sign)
    mocker.patch.object(mac, "unlock_keychain", new=noop_async)
    mocker.patch.object(mac, "verify_app_signature", new=noop_async)
    mocker.patch.object(mac, "sign_widevine_dir", new=noop_async)
    if raises:
        with pytest.raises(IScriptError):
            await mac.sign_all_apps(config, sign_config, entitlements_path, all_paths, fake_provisioning_profile_path)
    else:
        await mac.sign_all_apps(config, sign_config, entitlements_path, all_paths, fake_provisioning_profile_path)


# tar_apps {{{1
@pytest.mark.parametrize("raises, artifact_prefix", ((True, "public/"), (False, "public/"), (False, "releng/partner/")))
@pytest.mark.asyncio
async def test_tar_apps(mocker, tmpdir, raises, artifact_prefix):
    """``tar_apps`` runs tar concurrently for each ``App``, creating the
    app ``target_bundle_path``s, and raises any exceptions hit along the way.

    """

    async def fake_raise_future_exceptions(futures):
        await asyncio.wait(futures)
        if raises:
            raise IScriptError("foo")

    work_dir = os.path.join(tmpdir, "work")
    config = {"artifact_dir": os.path.join(tmpdir, "artifact")}
    all_paths = []
    expected = []
    for i in range(3):
        parent_dir = os.path.join(work_dir, str(i))
        app_name = "{}.app".format(i)
        makedirs(parent_dir)
        # touch parent_dir/app_name
        with open(os.path.join(parent_dir, app_name), "w") as fh:
            fh.write("foo")
        orig_path = os.path.join(work_dir, "cot", "foo", artifact_prefix, "build", str(i), f"{i}.tar.gz")
        # overload pkg_path to track i
        all_paths.append(
            mac.App(
                parent_dir=parent_dir,
                app_name=app_name,
                app_path=os.path.join(parent_dir, app_name),
                artifact_prefix=artifact_prefix,
                orig_path=orig_path,
                pkg_path=str(i),
            )
        )
        expected.append(os.path.join(config["artifact_dir"], artifact_prefix, "build", "{}/{}.tar.gz".format(i, i)))

    mocker.patch.object(mac, "run_command", new=noop_async)
    mocker.patch.object(mac, "raise_future_exceptions", new=fake_raise_future_exceptions)
    if raises:
        with pytest.raises(IScriptError):
            await mac.tar_apps(config, all_paths)
    else:
        assert await mac.tar_apps(config, all_paths) is None
        assert [x.target_bundle_path for x in all_paths] == expected
        for path in expected:
            assert os.path.isdir(os.path.dirname(path))


# create_pkg_files {{{1
@pytest.mark.parametrize(
    "pkg_cert_id, should_raise, requirements_path",
    (
        (None, True, None),
        (None, False, None),
        ("pkg.cert", False, None),
        (None, False, "requirements.plist"),
    ),
)
@pytest.mark.asyncio
async def test_create_pkg_files(mocker, pkg_cert_id, should_raise, requirements_path):
    """``create_pkg_files`` runs pkgbuild concurrently for each ``App``, and
    raises any exceptions hit along the way.

    """

    async def fake_retry_async(**kwargs):
        cmd = kwargs["kwargs"]["cmd"]
        assert cmd[0] in ("pkgbuild", "productbuild", "productsign")
        if should_raise:
            raise kwargs["kwargs"]["exception"]("foo")

        if cmd[0] == "productbuild":
            if requirements_path:
                assert "--product" in cmd
                assert requirements_path in cmd
                assert cmd.index("--product") + 1 == cmd.index(requirements_path)
            else:
                assert "--product" not in cmd
                assert requirements_path not in cmd

    sign_config = {"pkg_cert_id": pkg_cert_id, "signing_keychain": "signing.keychain"}
    config = {"concurrency_limit": 2}
    all_paths = []
    for i in range(3):
        all_paths.append(mac.App(app_path="foo/{}/{}.app".format(i, i), parent_dir="foo/{}".format(i)))
    mocker.patch.object(mac, "retry_async", new=fake_retry_async)
    mocker.patch.object(mac, "copy2", new=noop_sync)
    if should_raise:
        with pytest.raises(IScriptError):
            await mac.create_pkg_files(config, sign_config, all_paths, requirements_plist_path=requirements_path)
    else:
        assert await mac.create_pkg_files(config, sign_config, all_paths, requirements_plist_path=requirements_path) is None


# copy_pkgs_to_artifact_dir {{{1
@pytest.mark.parametrize("artifact_prefix", ("public/", "releng/partner/"))
@pytest.mark.asyncio
async def test_copy_pkgs_to_artifact_dir(tmpdir, artifact_prefix):
    """``copy_pkgs_to_artifact_dir`` creates all needed parent directories and
    copies pkg artifacts successfully.

    """
    num_pkgs = 3
    work_dir = os.path.join(str(tmpdir), "work")
    artifact_dir = os.path.join(str(tmpdir), "artifact")
    config = {"artifact_dir": artifact_dir, "work_dir": work_dir}
    all_paths = []
    expected_paths = []
    for i in range(num_pkgs):
        app = mac.App(
            pkg_path=os.path.join(work_dir, str(i), "target.pkg".format(i)),
            artifact_prefix=artifact_prefix,
            orig_path=os.path.join(work_dir, f"cot/taskId/{artifact_prefix}build/{i}/target-{i}.tar.gz"),
        )
        expected_path = os.path.join(artifact_dir, f"{artifact_prefix}build/{i}/target-{i}.pkg")
        expected_paths.append(expected_path)
        makedirs(os.path.dirname(app.pkg_path))
        with open(app.pkg_path, "w") as fh:
            fh.write(expected_path)
        all_paths.append(app)

    await mac.copy_pkgs_to_artifact_dir(config, all_paths)
    for i in range(num_pkgs):
        expected_path = expected_paths[i]
        assert os.path.exists(expected_path)
        assert expected_path == all_paths[i].target_pkg_path
        with open(expected_path) as fh:
            assert fh.read() == expected_path


# download_entitlements_file {{{1
@pytest.mark.parametrize(
    "url, use_entitlements, raises, expected",
    (("foo", True, False, "work/browser.entitlements.txt"), ("foo", False, False, None), (None, True, KeyError, None)),
)
@pytest.mark.asyncio
async def test_download_entitlements_file(url, use_entitlements, raises, expected, mocker):
    """``download_entitlements_file`` downloads the specified entitlements-url
    and returns the path. If no entitlements-url is specified, it returns
    ``None``.

    """
    mocker.patch.object(mac, "retry_async", new=noop_async)
    config = {"work_dir": "work"}
    task = {"payload": {}}
    sign_config = {"sign_with_entitlements": use_entitlements}
    if url:
        task["payload"]["entitlements-url"] = url
    if raises:
        with pytest.raises(raises):
            await mac.download_entitlements_file(config, sign_config, task)
    else:
        assert await mac.download_entitlements_file(config, sign_config, task) == expected


# download_provisioning_profile {{{1
@pytest.mark.parametrize(
    "url, expected",
    (("foo", "work/provisioning.profile"), (None, None)),
)
@pytest.mark.asyncio
async def test_download_provisioning_profile(url, expected, mocker):
    """``download_provisioning_profile`` downloads the specified
    provisioning-profile-url and returns the path. If no
    provisioning-profile-url is specified, it returns ``None``.

    """
    mocker.patch.object(mac, "retry_async", new=noop_async)
    config = {"work_dir": "work"}
    task = {"payload": {}}
    if url:
        task["payload"]["provisioning-profile-url"] = url
    assert await mac.download_provisioning_profile(config, task) == expected


# download_requirements_plist_file {{{1
@pytest.mark.parametrize(
    "url, expected",
    (("foo", "work/requirements.plist"), (None, None)),
)
@pytest.mark.asyncio
async def test_download_requirements_plist_file(url, expected, mocker):
    """``download_requirements_plist_file`` downloads the specified
    requirements-plist-url and returns the path. If no
    requirements-plist-url is specified, it returns ``None``.

    """
    mocker.patch.object(mac, "retry_async", new=noop_async)
    config = {"work_dir": "work"}
    task = {"payload": {}}
    if url:
        task["payload"]["requirements-plist-url"] = url
    assert await mac.download_requirements_plist_file(config, task) == expected


# sign_behavior {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize("use_langpack", (False, True))
async def test_sign_behavior(mocker, tmpdir, use_langpack):
    """Mock ``sign_behavior`` for full line coverage."""

    artifact_dir = os.path.join(str(tmpdir), "artifact")
    work_dir = os.path.join(str(tmpdir), "work")
    config = {
        "artifact_dir": artifact_dir,
        "work_dir": work_dir,
        "mac_config": {
            "dep": {
                "designated_requirements": "",  # put this here bc it's easier
                "signing_keychain": "keychain_path",
                "sign_with_entitlements": False,
                "identity": "id",
                "keychain_password": "keychain_password",
                "pkg_cert_id": "cert_id",
            }
        },
    }

    task = {
        "payload": {
            "upstreamArtifacts": [
                {"taskId": "task1", "formats": ["macapp"], "paths": ["public/build/1/target.tar.gz", "public/build/2/target.tar.gz"]},
                {"taskId": "task2", "paths": ["public/build/3/target.tar.gz"], "formats": ["macapp"]},
            ]
        }
    }
    if use_langpack:
        mocker.patch.object(mac, "sign_langpacks", new=noop_async)
        task["payload"]["upstreamArtifacts"].append({"taskId": "task3", "formats": ["autograph_langpack"], "paths": ["public/build3/target.langpack.xpi"]})

    mocker.patch.object(os, "listdir", return_value=[])
    mocker.patch.object(mac, "run_command", new=noop_async)
    mocker.patch.object(mac, "unlock_keychain", new=noop_async)
    mocker.patch.object(mac, "get_bundle_executable", return_value="bundle_executable")
    mocker.patch.object(mac, "get_app_dir", return_value=os.path.join(work_dir, "foo/bar.app"))
    mocker.patch.object(mac, "get_sign_config", return_value=config["mac_config"]["dep"])
    mocker.patch.object(mac, "sign_widevine_dir", new=noop_async)
    await mac.sign_behavior(config, task)


# sign_and_pkg_behavior {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize("use_langpack", (False, True))
async def test_sign_and_pkg_behavior(mocker, tmpdir, use_langpack):
    """Mock ``sign_and_pkg_behavior`` for full line coverage."""

    artifact_dir = os.path.join(str(tmpdir), "artifact")
    work_dir = os.path.join(str(tmpdir), "work")
    config = {
        "artifact_dir": artifact_dir,
        "work_dir": work_dir,
        "mac_config": {
            "dep": {
                "designated_requirements": "",  # put this here bc it's easier
                "signing_keychain": "keychain_path",
                "sign_with_entitlements": False,
                "identity": "id",
                "keychain_password": "keychain_password",
                "pkg_cert_id": "cert_id",
            }
        },
    }

    task = {
        "payload": {
            "upstreamArtifacts": [
                {
                    "taskId": "task1",
                    "formats": ["macapp", "autograph_widevine", "autograph_omnija"],
                    "paths": ["public/build/1/target.tar.gz", "public/build/2/target.tar.gz"],
                },
                {"taskId": "task2", "paths": ["public/build/3/target.tar.gz"], "formats": ["macapp", "widevine", "omnija"]},
            ]
        }
    }
    if use_langpack:
        mocker.patch.object(mac, "sign_langpacks", new=noop_async)
        task["payload"]["upstreamArtifacts"].append({"taskId": "task3", "formats": ["autograph_langpack"], "paths": ["public/build3/target.langpack.xpi"]})

    mocker.patch.object(os, "listdir", return_value=[])
    mocker.patch.object(mac, "run_command", new=noop_async)
    mocker.patch.object(mac, "unlock_keychain", new=noop_async)
    mocker.patch.object(mac, "get_bundle_executable", return_value="bundle_executable")
    mocker.patch.object(mac, "get_app_dir", return_value=os.path.join(work_dir, "foo/bar.app"))
    mocker.patch.object(mac, "copy_pkgs_to_artifact_dir", new=noop_async)
    mocker.patch.object(mac, "get_sign_config", return_value=config["mac_config"]["dep"])
    mocker.patch.object(mac, "sign_omnija_with_autograph", new=noop_async)
    mocker.patch.object(mac, "sign_widevine_dir", new=noop_async)
    await mac.sign_and_pkg_behavior(config, task)


# single_file_behavior {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "use_langpack,filename,format",
    ((False, "geckodriver", "mac_geckodriver"), (True, "foo", "mac_single_file"), (False, "geckodriver", "mac_single_file")),
)
async def test_single_file_behavior(mocker, tmpdir, use_langpack, filename, format):
    """Mock ``single_file_behavior`` for full line coverage."""

    artifact_dir = os.path.join(str(tmpdir), "artifact")
    work_dir = os.path.join(str(tmpdir), "work")
    config = {
        "artifact_dir": artifact_dir,
        "work_dir": work_dir,
        "mac_config": {
            "dep": {
                "designated_requirements": "",  # put this here bc it's easier
                "signing_keychain": "keychain_path",
                "sign_with_entitlements": False,
                "identity": "id",
                "keychain_password": "keychain_password",
                "pkg_cert_id": "cert_id",
            }
        },
    }

    task = {"payload": {"upstreamArtifacts": [{"taskId": "task1", "formats": [format], "paths": [f"public/build/1/{filename}.tar.gz"]}]}}
    if format == "mac_single_file":
        task["payload"]["upstreamArtifacts"][0]["singleFileGlobs"] = [filename]
    if use_langpack:
        mocker.patch.object(mac, "sign_langpacks", new=noop_async)
        task["payload"]["upstreamArtifacts"].append({"taskId": "task3", "formats": ["autograph_langpack"], "paths": ["public/build3/target.langpack.xpi"]})

    async def fake_extract(_, all_paths):
        for app in all_paths:
            assert "autograph_langpack" not in app.formats
            app.parent_dir = f"{work_dir}/0"
            touch(f"{app.parent_dir}/{filename}")

    mocker.patch.object(mac, "extract_all_apps", new=fake_extract)
    mocker.patch.object(mac, "run_command", new=noop_async)
    mocker.patch.object(mac, "unlock_keychain", new=noop_async)
    mocker.patch.object(mac, "get_sign_config", return_value=config["mac_config"]["dep"])
    await mac.single_file_behavior(config, task)
