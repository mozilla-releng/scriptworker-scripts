#!/usr/bin/env python
# coding=utf-8
"""Test iscript.mac
"""
import arrow
import asyncio
from functools import partial
import mock
import os
import pexpect
import plistlib
import pytest
import iscript.mac as mac
from iscript.exceptions import (
    InvalidNotarization,
    IScriptError,
    TimeoutError,
    UnknownAppDir,
)
from scriptworker_client.utils import makedirs


# helpers {{{1
async def noop_async(*args, **kwargs):
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
    "path, expected, raises",
    (
        ("foo/bar/target.tar.gz", "czf", False),
        ("foo/bar/target.tar.bz2", "cjf", False),
        ("foo/bar/target.tar.xz", None, True),
    ),
)
def test_get_tar_create_options(path, expected, raises):
    if raises:
        with pytest.raises(IScriptError):
            mac._get_tar_create_options(path)
    else:
        assert mac._get_tar_create_options(path) == expected


@pytest.mark.parametrize(
    "path, expected, raises",
    (
        ("foo/bar/target.tar.gz", "foo/bar/target.pkg", False),
        ("foo/bar/target.tar.bz2", "foo/bar/target.pkg", False),
        ("foo/bar/target.tar.xz", None, True),
    ),
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
    expected = [
        ["foo/1/1.app", "1.app"],
        ["foo/2/2.app", "2.app"],
        ["foo/4/4.app", "4.app"],
    ]
    for app in all_paths:
        mac.set_app_path_and_name(app)
        assert [app.app_path, app.app_name] == expected.pop(0)


# get_bundle_executable {{{1
def test_get_bundle_executable(mocker):
    """``get_bundle_executable`` returns the CFBundleExecutable.

    """
    mocker.patch.object(
        plistlib, "readPlist", return_value={"CFBundleExecutable": "main"}
    )
    assert mac.get_bundle_executable("foo") == "main"


# sign_app {{{1
@pytest.mark.parametrize(
    "sign_with_entitlements,has_clearkey", ((True, True), (False, False))
)
@pytest.mark.asyncio
async def test_sign_app(mocker, tmpdir, sign_with_entitlements, has_clearkey):
    """Render ``sign_app`` noop and verify we have complete code coverage.

    """
    key_config = {
        "identity": "id",
        "signing_keychain": "keychain",
        "sign_with_entitlements": sign_with_entitlements,
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
    await mac.sign_app(key_config, app_path, entitlements_path)


# verify_app_signature {{{1
@pytest.mark.asyncio
async def test_verify_app_signature_noop(mocker):
    """``verify_app_signature`` is noop when ``verify_mac_signature`` is False."""

    key_config = {"verify_mac_signature": False}
    # If we actually run_command, raise to show we're doing too much
    mocker.patch.object(mac, "run_command", new=fail_async)
    await mac.verify_app_signature(key_config, mac.App())


# unlock_keychain {{{1
def fake_spawn(val, *args, **kwargs):
    return val


@pytest.mark.parametrize("results", ([1, 0], [0]))
@pytest.mark.asyncio
async def test_unlock_keychain_successful(results, mocker):
    """Mock a successful keychain unlock.

    """

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
    """``unlock_keychain`` raises a ``TimeoutError`` on pexpect timeout.

    """

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
    """``unlock_keychain`` throws an ``IScriptError`` on non-zero exit status.

    """
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
@pytest.mark.parametrize(
    "apps, raises",
    (
        ([], True),
        (["foo.app"], False),
        (["foo.notanapp"], True),
        (["one.app", "two.app"], True),
    ),
)
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
    "path, expected, raises",
    (
        ("public/build/foo", "public/", False),
        ("releng/partner/bar", "releng/partner/", False),
        ("unknown/prefix/baz", None, True),
    ),
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
                {
                    "paths": ["public/bar", "public/baz"],
                    "taskId": "task2",
                    "formats": ["macapp"],
                },
            ]
        }
    }
    paths = []
    apps = mac.get_app_paths(config, task)
    for app in apps:
        assert isinstance(app, mac.App)
        paths.append(app.orig_path)
    assert paths == [
        "work/cot/task1/public/foo",
        "work/cot/task2/public/bar",
        "work/cot/task2/public/baz",
    ]


# extract_all_apps {{{1
@pytest.mark.parametrize(
    "suffix, command, raises",
    (
        (
            "dmg",
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "src",
                "iscript",
                "data",
                "unpack-diskimage",
            ),
            False,
        ),
        ("tar.gz", "tar", False),
        ("tar.bz2", "tar", False),
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
    config = {"work_dir": work_dir}
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


# create_all_notarization_zipfiles {{{1
@pytest.mark.parametrize("raises", (True, False))
@pytest.mark.asyncio
async def test_create_all_notarization_zipfiles(mocker, tmpdir, raises):
    """``create_all_notarization_zipfiles`` calls ``zip -r``, and raises on failure.

    """

    async def fake_run_command(*args, **kwargs):
        assert args[0][0:2] == ["zip", "-r"]
        if raises:
            raise IScriptError("foo")

    mocker.patch.object(mac, "run_command", new=fake_run_command)
    all_paths = []
    work_dir = str(tmpdir)
    for i in range(3):
        parent_dir = os.path.join(work_dir, str(i))
        app_name = "fx {}.app".format(str(i))
        app_path = os.path.join(parent_dir, app_name)
        all_paths.append(
            mac.App(parent_dir=parent_dir, app_name=app_name, app_path=app_path)
        )

    if raises:
        with pytest.raises(IScriptError):
            await mac.create_all_notarization_zipfiles(all_paths)
    else:
        await mac.create_all_notarization_zipfiles(all_paths)


# create_one_notarization_zipfile {{{1
@pytest.mark.parametrize("raises", (True, False))
@pytest.mark.asyncio
async def test_create_one_notarization_zipfile(mocker, tmpdir, raises):
    """``create_one_notarization_zipfile`` calls the expected cmdline, and raises on
    failure.

    """
    work_dir = str(tmpdir)

    async def fake_run_command(*args, **kwargs):
        assert args[0] == [
            "zip",
            "-r",
            os.path.join(work_dir, "app_path.zip"),
            "0/0.app",
            "1/1.app",
            "2/2.app",
        ]
        if raises:
            raise IScriptError("foo")

    mocker.patch.object(mac, "run_command", new=fake_run_command)
    all_paths = []
    for i in range(3):
        all_paths.append(
            mac.App(app_path=os.path.join(work_dir, str(i), "{}.app".format(i)))
        )
    if raises:
        with pytest.raises(IScriptError):
            await mac.create_one_notarization_zipfile(work_dir, all_paths)
    else:
        await mac.create_one_notarization_zipfile(work_dir, all_paths)


# sign_all_apps {{{1
@pytest.mark.parametrize("raises", (True, False))
@pytest.mark.asyncio
async def test_sign_all_apps(mocker, tmpdir, raises):
    """``sign_all_apps`` calls ``sign`` and raises on failure.

    """
    key_config = {"x": "y"}
    config = {}
    entitlements_path = "fake_entitlements_path"
    work_dir = str(tmpdir)
    all_paths = []
    app_paths = []
    for i in range(3):
        app_path = "{}.app".format(str(i))
        app_paths.append(app_path)
        all_paths.append(
            mac.App(parent_dir=os.path.join(work_dir, str(i)), app_path=app_path)
        )

    async def fake_sign(arg1, arg2, arg3):
        assert arg1 == key_config
        assert arg2 in app_paths
        assert arg3 == entitlements_path
        if raises:
            raise IScriptError("foo")

    mocker.patch.object(mac, "set_app_path_and_name", return_value=None)
    mocker.patch.object(mac, "sign_app", new=fake_sign)
    mocker.patch.object(mac, "verify_app_signature", new=noop_async)
    mocker.patch.object(mac, "sign_widevine_dir", new=noop_async)
    if raises:
        with pytest.raises(IScriptError):
            await mac.sign_all_apps(config, key_config, entitlements_path, all_paths)
    else:
        await mac.sign_all_apps(config, key_config, entitlements_path, all_paths)


# get_bundle_id {{{1
@pytest.mark.parametrize("task_id", (None, "asdf"))
@pytest.mark.parametrize("counter", (None, 3))
def test_get_bundle_id(mocker, task_id, counter):
    """``get_bundle_id`` returns a unique bundle id

    """
    now = mock.MagicMock()
    now.timestamp = 51
    now.microsecond = 50
    mocker.patch.object(arrow, "utcnow", return_value=now)
    base = "org.foo.base"
    expected = base
    if task_id:
        expected = "{}.{}.{}{}".format(
            expected, task_id, now.timestamp, now.microsecond
        )
        mocker.patch.object(os, "environ", new={"TASK_ID": task_id})
    else:
        expected = "{}.None.{}{}".format(expected, now.timestamp, now.microsecond)
    if counter:
        expected = "{}.{}".format(expected, counter)
    assert mac.get_bundle_id(base, counter=counter) == expected


# get_uuid_from_log {{{1
@pytest.mark.parametrize(
    "uuid, raises",
    (
        ("07307e2c-db26-494c-8630-cfa239d4b86b", False),
        ("d4d31c49-c075-4ea1-bb7f-150c74f608e1", False),
        ("d4d31c49-c075-4ea1-bb7f-150c74f608e1", "missing file"),
        ("%%%%\\\\=", "missing uuid"),
    ),
)
def test_get_uuid_from_log(tmpdir, uuid, raises):
    """``get_uuid_from_log`` returns the correct uuid from the logfile if present.
    It raises if it has problems finding the uuid in the log.

    """
    log_path = os.path.join(str(tmpdir), "log")
    if raises != "missing file":
        with open(log_path, "w") as fh:
            fh.write("foo\nbar\nbaz\n RequestUUID = {} \nblah\n".format(uuid))
    if raises:
        with pytest.raises(IScriptError):
            mac.get_uuid_from_log(log_path)
    else:
        assert mac.get_uuid_from_log(log_path) == uuid


# get_notarization_status_from_log {{{1
@pytest.mark.parametrize(
    "has_log, status, expected",
    (
        (True, "invalid", "invalid"),
        (True, "success", "success"),
        (True, "unknown", None),
        (False, None, None),
    ),
)
def test_get_notarization_status_from_log(tmpdir, has_log, status, expected):
    """``get_notarization_status_from_log`` finds a valid status in the log
    and returns it. If there is a problem or missing/unknown status, it
    returns ``None``.

    """
    log_path = os.path.join(str(tmpdir), "log")
    if has_log:
        with open(log_path, "w") as fh:
            fh.write("foo\nbar\nbaz\n Status: {} \nblah\n".format(status))
    assert mac.get_notarization_status_from_log(log_path) == expected


# wrap_notarization_with_sudo {{{1
@pytest.mark.parametrize("raises", (True, False))
@pytest.mark.asyncio
async def test_wrap_notarization_with_sudo(mocker, tmpdir, raises):
    """``wrap_notarization_with_sudo`` chunks its requests into one concurrent
    request per each of the ``local_notarization_accounts``. It doesn't log
    the password.

    """
    futures_len = [3, 3, 2]
    pw = "test_apple_password"

    async def fake_retry_async(_, args, kwargs):
        cmd = args[0]
        end = len(cmd) - 1
        assert cmd[0] == "sudo"
        log_cmd = kwargs["log_cmd"]
        assert cmd[0:end] == log_cmd[0:end]
        assert cmd[end] != log_cmd[end]
        assert cmd[end] == pw
        assert log_cmd[end].replace("*", "") == ""

    async def fake_raise_future_exceptions(futures, **kwargs):
        """``raise_future_exceptions`` mocker."""

        await asyncio.wait(futures)
        assert len(futures) == futures_len.pop(0)
        if raises:
            raise IScriptError("foo")

    def fake_get_uuid_from_log(path):
        return path

    work_dir = str(tmpdir)
    config = {"local_notarization_accounts": ["acct0", "acct1", "acct2"]}
    key_config = {
        "base_bundle_id": "org.iscript.test",
        "apple_notarization_account": "test_apple_account",
        "apple_notarization_password": pw,
    }
    all_paths = []
    expected = {}
    # Let's create 8 apps, with 3 sudo accounts, so we expect batches of 3, 3, 2
    for i in range(8):
        parent_dir = os.path.join(work_dir, str(i))
        notarization_log_path = f"{parent_dir}-notarization.log"
        all_paths.append(
            mac.App(
                parent_dir=parent_dir,
                zip_path=os.path.join(parent_dir, "{}.zip".format(i)),
            )
        )
        expected[notarization_log_path] = notarization_log_path

    mocker.patch.object(mac, "retry_async", new=fake_retry_async)
    mocker.patch.object(
        mac, "raise_future_exceptions", new=fake_raise_future_exceptions
    )
    mocker.patch.object(mac, "get_uuid_from_log", new=fake_get_uuid_from_log)
    if raises:
        with pytest.raises(IScriptError):
            await mac.wrap_notarization_with_sudo(config, key_config, all_paths)
    else:
        assert (
            await mac.wrap_notarization_with_sudo(config, key_config, all_paths)
            == expected
        )


# notarize_no_sudo {{{1
@pytest.mark.parametrize("raises", (True, False))
@pytest.mark.asyncio
async def test_notarize_no_sudo(mocker, tmpdir, raises):
    """``notarize_no_sudo`` creates a single request to notarize that doesn't
    log the password.

    """
    pw = "test_apple_password"

    async def fake_retry_async(_, args, kwargs):
        cmd = args[0]
        end = len(cmd) - 1
        assert cmd[0] == "xcrun"
        log_cmd = kwargs["log_cmd"]
        assert cmd[0:end] == log_cmd[0:end]
        assert cmd[end] != log_cmd[end]
        assert cmd[end] == pw
        assert log_cmd[end].replace("*", "") == ""
        if raises:
            raise IScriptError("foo")

    def fake_get_uuid_from_log(path):
        return path

    work_dir = str(tmpdir)
    zip_path = os.path.join(work_dir, "zip_path")
    log_path = os.path.join(work_dir, "notarization.log")
    key_config = {
        "base_bundle_id": "org.iscript.test",
        "apple_notarization_account": "test_apple_account",
        "apple_notarization_password": pw,
    }
    expected = {log_path: log_path}

    mocker.patch.object(mac, "retry_async", new=fake_retry_async)
    mocker.patch.object(mac, "get_uuid_from_log", new=fake_get_uuid_from_log)
    if raises:
        with pytest.raises(IScriptError):
            await mac.notarize_no_sudo(work_dir, key_config, zip_path)
    else:
        assert await mac.notarize_no_sudo(work_dir, key_config, zip_path) == expected


# poll_notarization_uuid {{{1
@pytest.mark.parametrize(
    "statuses, exception",
    (
        (["success"], None),
        ([None, "success"], None),
        ([None], IScriptError),
        (["invalid"], InvalidNotarization),
        (
            [None, None, None, None, None, None, None, None, None, None, None],
            TimeoutError,
        ),
    ),
)
@pytest.mark.asyncio
async def test_poll_notarization_uuid(mocker, tmpdir, statuses, exception):
    """``poll_notarization_uuid``: returns ``None`` on success; raises a
    ``TimeoutError`` on timeout; raises ``IScriptError`` on failure; and raises
    ``InvalidNotarization`` on ``invalid`` status from Apple. Also, it doesn't
    log passwords.

    """
    pw = "test_apple_password"

    async def fake_retry_async(_, args, kwargs):
        cmd = args[0]
        end = len(cmd) - 1
        assert cmd[0] == "xcrun"
        log_cmd = kwargs["log_cmd"]
        assert cmd[0:end] == log_cmd[0:end]
        assert cmd[end] != log_cmd[end]
        assert cmd[end] == pw
        assert log_cmd[end].replace("*", "") == ""
        if exception is IScriptError:
            raise IScriptError("foo")

    def fake_get_notarization_status_from_log(path):
        status = statuses.pop(0)
        return status

    mocker.patch.object(mac, "retry_async", new=fake_retry_async)
    mocker.patch.object(
        mac,
        "get_notarization_status_from_log",
        new=fake_get_notarization_status_from_log,
    )
    if exception:
        with pytest.raises(exception):
            await mac.poll_notarization_uuid(
                "uuid", "user", pw, 0.5, "/dev/null", sleep_time=0.1
            )
    else:
        assert (
            await mac.poll_notarization_uuid(
                "uuid", "user", pw, 1, "/dev/null", sleep_time=0.1
            )
            is None
        )


# poll_all_notarization_status {{{1
@pytest.mark.parametrize(
    "poll_uuids, raises",
    (
        ({"uuid": "log_path"}, True),
        ({"uuid": "log_path"}, False),
        ({"uuid1": "log_path1", "uuid2": "log_path2"}, False),
    ),
)
@pytest.mark.asyncio
async def test_poll_all_notarization_status(mocker, tmpdir, poll_uuids, raises):
    """```poll_all_notarization_status`` concurrently runs a number of
    ``poll_notarization_uuid`` calls, and raises if any of those calls raise.

    """

    async def fake_raise_future_exceptions(futures):
        await asyncio.wait(futures)
        assert len(futures) == len(poll_uuids)
        if raises:
            raise IScriptError("foo")

    key_config = {
        "apple_notarization_account": "test_apple_account",
        "apple_notarization_password": "test_apple_password",
        "notarization_poll_timeout": 1,
    }

    mocker.patch.object(
        mac, "raise_future_exceptions", new=fake_raise_future_exceptions
    )
    mocker.patch.object(mac, "poll_notarization_uuid", new=noop_async)
    if raises:
        with pytest.raises(IScriptError):
            await mac.poll_all_notarization_status(key_config, poll_uuids)

    else:
        assert await mac.poll_all_notarization_status(key_config, poll_uuids) is None


# staple_notarization {{{1
@pytest.mark.parametrize("raises", (True, False))
@pytest.mark.asyncio
async def test_staple_notarization(mocker, raises):
    """``staple_notarization`` runs stapling concurrently for each ``App``, and raises
    any exceptions hit along the way.

    """

    async def fake_run_command(*args, **kwargs):
        assert args[0][0] == "xcrun"
        if raises:
            raise IScriptError("foo")

    all_paths = []
    for i in range(3):
        parent_dir = str(i)
        app_name = f"{i}.app"
        app_path = os.path.join(parent_dir, app_name)
        all_paths.append(
            mac.App(parent_dir=parent_dir, app_name=app_name, app_path=app_path)
        )
    mocker.patch.object(mac, "run_command", new=fake_run_command)
    if raises:
        with pytest.raises(IScriptError):
            await mac.staple_notarization(all_paths)
    else:
        assert await mac.staple_notarization(all_paths) is None


# tar_apps {{{1
@pytest.mark.parametrize(
    "raises, artifact_prefix",
    ((True, "public/"), (False, "public/"), (False, "releng/partner/")),
)
@pytest.mark.asyncio
async def test_tar_apps(mocker, tmpdir, raises, artifact_prefix):
    """``tar_apps`` runs tar concurrently for each ``App``, creating the
    app ``target_tar_path``s, and raises any exceptions hit along the way.

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
        orig_path = os.path.join(
            work_dir, "cot", "foo", artifact_prefix, "build", str(i), f"{i}.tar.gz"
        )
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
        expected.append(
            os.path.join(
                config["artifact_dir"],
                artifact_prefix,
                "build",
                "{}/{}.tar.gz".format(i, i),
            )
        )

    mocker.patch.object(mac, "run_command", new=noop_async)
    mocker.patch.object(
        mac, "raise_future_exceptions", new=fake_raise_future_exceptions
    )
    if raises:
        with pytest.raises(IScriptError):
            await mac.tar_apps(config, all_paths)
    else:
        assert await mac.tar_apps(config, all_paths) is None
        assert [x.target_tar_path for x in all_paths] == expected
        for path in expected:
            assert os.path.isdir(os.path.dirname(path))


# create_pkg_files {{{1
@pytest.mark.parametrize(
    "pkg_cert_id, raises", ((None, True), (None, False), ("pkg.cert", False))
)
@pytest.mark.asyncio
async def test_create_pkg_files(mocker, pkg_cert_id, raises):
    """``create_pkg_files`` runs pkgbuild concurrently for each ``App``, and
    raises any exceptions hit along the way.

    """

    async def fake_run_command(cmd, **kwargs):
        assert cmd[0:2] == ["sudo", "pkgbuild"]
        if raises:
            raise IScriptError("foo")

    key_config = {"pkg_cert_id": pkg_cert_id, "signing_keychain": "signing.keychain"}
    config = {"concurrency_limit": 2}
    all_paths = []
    for i in range(3):
        all_paths.append(
            mac.App(
                app_path="foo/{}/{}.app".format(i, i), parent_dir="foo/{}".format(i)
            )
        )
    mocker.patch.object(mac, "run_command", new=fake_run_command)
    if raises:
        with pytest.raises(IScriptError):
            await mac.create_pkg_files(config, key_config, all_paths)
    else:
        assert await mac.create_pkg_files(config, key_config, all_paths) is None


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
            orig_path=os.path.join(
                work_dir, f"cot/taskId/{artifact_prefix}build/{i}/target-{i}.tar.gz"
            ),
        )
        expected_path = os.path.join(
            artifact_dir, f"{artifact_prefix}build/{i}/target-{i}.pkg"
        )
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
    (
        ("foo", True, False, "work/browser.entitlements.txt"),
        ("foo", False, False, None),
        (None, True, KeyError, None),
    ),
)
@pytest.mark.asyncio
async def test_download_entitlements_file(
    url, use_entitlements, raises, expected, mocker
):
    """``download_entitlements_file`` downloads the specified entitlements-url
    and returns the path. If no entitlements-url is specified, it returns
    ``None``.

    """
    mocker.patch.object(mac, "retry_async", new=noop_async)
    config = {"work_dir": "work"}
    task = {"payload": {}}
    key_config = {"sign_with_entitlements": use_entitlements}
    if url:
        task["payload"]["entitlements-url"] = url
    if raises:
        with pytest.raises(raises):
            await mac.download_entitlements_file(config, key_config, task)
    else:
        assert (
            await mac.download_entitlements_file(config, key_config, task) == expected
        )


# sign_behavior {{{1
@pytest.mark.asyncio
async def test_sign_behavior(mocker, tmpdir):
    """Mock ``sign_behavior`` for full line coverage."""

    artifact_dir = os.path.join(str(tmpdir), "artifact")
    work_dir = os.path.join(str(tmpdir), "work")
    config = {
        "artifact_dir": artifact_dir,
        "work_dir": work_dir,
        "local_notarization_accounts": ["acct0", "acct1", "acct2"],
        "mac_config": {
            "dep": {
                "notarize_type": "",
                "signing_keychain": "keychain_path",
                "sign_with_entitlements": False,
                "base_bundle_id": "org.test",
                "identity": "id",
                "keychain_password": "keychain_password",
                "pkg_cert_id": "cert_id",
                "apple_notarization_account": "apple_account",
                "apple_notarization_password": "apple_password",
                "notarization_poll_timeout": 2,
            }
        },
    }

    task = {
        "payload": {
            "upstreamArtifacts": [
                {
                    "taskId": "task1",
                    "formats": ["macapp"],
                    "paths": [
                        "public/build/1/target.tar.gz",
                        "public/build/2/target.tar.gz",
                    ],
                },
                {
                    "taskId": "task2",
                    "paths": ["public/build/3/target.tar.gz"],
                    "formats": ["macapp"],
                },
            ]
        }
    }

    mocker.patch.object(os, "listdir", return_value=[])
    mocker.patch.object(mac, "run_command", new=noop_async)
    mocker.patch.object(mac, "unlock_keychain", new=noop_async)
    mocker.patch.object(mac, "get_bundle_executable", return_value="bundle_executable")
    mocker.patch.object(
        mac, "get_app_dir", return_value=os.path.join(work_dir, "foo/bar.app")
    )
    mocker.patch.object(mac, "get_key_config", return_value=config["mac_config"]["dep"])
    mocker.patch.object(mac, "sign_widevine_dir", new=noop_async)
    await mac.sign_behavior(config, task)


# sign_and_pkg_behavior {{{1
@pytest.mark.asyncio
async def test_sign_and_pkg_behavior(mocker, tmpdir):
    """Mock ``sign_and_pkg_behavior`` for full line coverage."""

    artifact_dir = os.path.join(str(tmpdir), "artifact")
    work_dir = os.path.join(str(tmpdir), "work")
    config = {
        "artifact_dir": artifact_dir,
        "work_dir": work_dir,
        "local_notarization_accounts": ["acct0", "acct1", "acct2"],
        "mac_config": {
            "dep": {
                "notarize_type": "",
                "signing_keychain": "keychain_path",
                "sign_with_entitlements": False,
                "base_bundle_id": "org.test",
                "identity": "id",
                "keychain_password": "keychain_password",
                "pkg_cert_id": "cert_id",
                "apple_notarization_account": "apple_account",
                "apple_notarization_password": "apple_password",
                "notarization_poll_timeout": 2,
            }
        },
    }

    task = {
        "payload": {
            "upstreamArtifacts": [
                {
                    "taskId": "task1",
                    "formats": ["macapp", "autograph_widevine", "autograph_omnija"],
                    "paths": [
                        "public/build/1/target.tar.gz",
                        "public/build/2/target.tar.gz",
                    ],
                },
                {
                    "taskId": "task2",
                    "paths": ["public/build/3/target.tar.gz"],
                    "formats": ["macapp", "widevine", "omnija"],
                },
            ]
        }
    }

    mocker.patch.object(os, "listdir", return_value=[])
    mocker.patch.object(mac, "run_command", new=noop_async)
    mocker.patch.object(mac, "unlock_keychain", new=noop_async)
    mocker.patch.object(mac, "get_bundle_executable", return_value="bundle_executable")
    mocker.patch.object(
        mac, "get_app_dir", return_value=os.path.join(work_dir, "foo/bar.app")
    )
    mocker.patch.object(mac, "copy_pkgs_to_artifact_dir", new=noop_async)
    mocker.patch.object(mac, "get_key_config", return_value=config["mac_config"]["dep"])
    mocker.patch.object(mac, "sign_omnija_with_autograph", new=noop_async)
    mocker.patch.object(mac, "sign_widevine_dir", new=noop_async)
    await mac.sign_and_pkg_behavior(config, task)


# notarize_behavior {{{1
@pytest.mark.parametrize(
    "notarize_type", ("multi_account", "single_account", "single_zip")
)
@pytest.mark.asyncio
async def test_notarize_behavior(mocker, tmpdir, notarize_type):
    """Mock ``notarize_behavior`` for full line coverage."""

    artifact_dir = os.path.join(str(tmpdir), "artifact")
    work_dir = os.path.join(str(tmpdir), "work")
    config = {
        "artifact_dir": artifact_dir,
        "work_dir": work_dir,
        "local_notarization_accounts": ["acct0", "acct1", "acct2"],
        "mac_config": {
            "dep": {
                "notarize_type": notarize_type,
                "signing_keychain": "keychain_path",
                "sign_with_entitlements": False,
                "base_bundle_id": "org.test",
                "identity": "id",
                "keychain_password": "keychain_password",
                "pkg_cert_id": "cert_id",
                "apple_notarization_account": "apple_account",
                "apple_notarization_password": "apple_password",
                "notarization_poll_timeout": 2,
            }
        },
    }

    task = {
        "payload": {
            "upstreamArtifacts": [
                {
                    "taskId": "task1",
                    "formats": ["macapp", "widevine"],
                    "paths": [
                        "public/build/1/target.tar.gz",
                        "public/build/2/target.tar.gz",
                    ],
                },
                {
                    "taskId": "task2",
                    "paths": ["public/build/3/target.tar.gz"],
                    "formats": ["macapp", "widevine"],
                },
            ]
        }
    }

    mocker.patch.object(os, "listdir", return_value=[])
    mocker.patch.object(mac, "run_command", new=noop_async)
    mocker.patch.object(mac, "unlock_keychain", new=noop_async)
    mocker.patch.object(mac, "get_bundle_executable", return_value="bundle_executable")
    mocker.patch.object(mac, "poll_notarization_uuid", new=noop_async)
    mocker.patch.object(
        mac, "get_app_dir", return_value=os.path.join(work_dir, "foo/bar.app")
    )
    mocker.patch.object(mac, "get_notarization_status_from_log", return_value=None)
    mocker.patch.object(mac, "get_uuid_from_log", return_value="uuid")
    mocker.patch.object(mac, "copy_pkgs_to_artifact_dir", new=noop_async)
    mocker.patch.object(mac, "get_key_config", return_value=config["mac_config"]["dep"])
    mocker.patch.object(mac, "sign_widevine_dir", new=noop_async)
    await mac.notarize_behavior(config, task)


# pkg_behavior {{{1
@pytest.mark.asyncio
async def test_pkg_behavior(mocker, tmpdir):
    """Mock ``pkg_behavior`` for full line coverage."""

    artifact_dir = os.path.join(str(tmpdir), "artifact")
    work_dir = os.path.join(str(tmpdir), "work")
    config = {
        "artifact_dir": artifact_dir,
        "work_dir": work_dir,
        "local_notarization_accounts": ["acct0", "acct1", "acct2"],
        "mac_config": {
            "dep": {
                "notarize_type": "single_zip",
                "signing_keychain": "keychain_path",
                "base_bundle_id": "org.test",
                "identity": "id",
                "keychain_password": "keychain_password",
                "pkg_cert_id": "cert_id",
                "apple_notarization_account": "apple_account",
                "apple_notarization_password": "apple_password",
                "notarization_poll_timeout": 2,
            }
        },
    }

    task = {
        "payload": {
            "upstreamArtifacts": [
                {
                    "taskId": "task1",
                    "formats": ["macapp"],
                    "paths": [
                        "public/build/1/target.tar.gz",
                        "public/build/2/target.tar.gz",
                    ],
                },
                {
                    "taskId": "task2",
                    "paths": ["public/build/3/target.tar.gz"],
                    "formats": ["macapp", "widevine"],
                },
            ]
        }
    }

    mocker.patch.object(mac, "run_command", new=noop_async)
    mocker.patch.object(mac, "unlock_keychain", new=noop_async)
    mocker.patch.object(mac, "copy_pkgs_to_artifact_dir", new=noop_async)
    mocker.patch.object(mac, "get_key_config", return_value=config["mac_config"]["dep"])
    mocker.patch.object(
        mac, "get_app_dir", return_value=os.path.join(work_dir, "foo/bar.app")
    )
    await mac.pkg_behavior(config, task)
