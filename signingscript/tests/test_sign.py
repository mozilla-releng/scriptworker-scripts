import asyncio
import base64
import json
import os
import os.path
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from contextlib import contextmanager
from hashlib import sha256
from unittest import mock

import aiohttp
import pytest
import winsign.sign
from conftest import BASE_DIR, DEFAULT_SCOPE_PREFIX, SERVER_CONFIG_PATH, TEST_DATA_DIR, die, does_not_raise, noop_async, noop_sync
from scriptworker.utils import makedirs

import signingscript.sign as sign
import signingscript.utils as utils
from signingscript.exceptions import SigningScriptError
from signingscript.utils import get_hash

# helper constants, fixtures, functions {{{1
TEST_CERT_TYPE = "{}cert:dep-signing".format(DEFAULT_SCOPE_PREFIX)

INSTALL_DIR = os.path.dirname(sign.__file__)


def async_mock_return_value(value):
    """
    Return a value appropriate to assign to `mock.return_value` of an async function.

    Python 3.8 added asyncio support to mock, so setting `mock.return_value` to
    a `Future` cause the result of awaiting the result a future, rather than a
    value.
    """
    if sys.version_info >= (3, 8):
        return value
    else:
        future = asyncio.Future()
        future.set_result(value)
        return future


@contextmanager
def context_die(*args, **kwargs):
    raise SigningScriptError("dying")


def is_tarfile(archive):
    try:
        import tarfile

        tarfile.open(archive)
    except tarfile.ReadError:
        return False
    return True


class MockedSession:
    def __init__(self, signed_file=None, signature=None, exception=None):
        self.signed_file = signed_file
        self.exception = exception
        self.signature = signature
        self.post = mock.MagicMock(wraps=self.post)

    async def post(self, *args, **kwargs):
        resp = mock.MagicMock()
        resp.status = 200
        resp.json.return_value = asyncio.Future()
        if self.signed_file:
            resp.json.return_value.set_result([{"signed_file": self.signed_file}])
        if self.signature:
            resp.json.return_value.set_result([{"signature": self.signature}])
        if self.exception:
            resp.json.side_effect = self.exception
        return resp


async def assert_file_permissions(archive):
    with tarfile.open(archive, mode="r") as t:
        for member in t.getmembers():
            assert member.uid == 0
            assert member.gid == 0


async def helper_archive(context, filename, create_fn, extract_fn, *args):
    tmpdir = context.config["artifact_dir"]
    archive = os.path.join(context.config["work_dir"], filename)
    # Add a directory to tickle the tarfile isfile() call
    files = [__file__, SERVER_CONFIG_PATH]
    await create_fn(context, archive, [__file__, SERVER_CONFIG_PATH], *args, tmp_dir=BASE_DIR)
    # Not relevant for zip
    if is_tarfile(archive):
        await assert_file_permissions(archive)
    await extract_fn(context, archive, *args, tmp_dir=tmpdir)
    for path in files:
        target_path = os.path.join(tmpdir, os.path.relpath(path, BASE_DIR))
        assert os.path.exists(target_path)
        assert os.path.isfile(target_path)
        hash1 = get_hash(path)
        hash2 = get_hash(target_path)
        assert hash1 == hash2


# get_autograph_config {{{1
@pytest.mark.parametrize(
    "formats,expected",
    ((["autograph_marsha384"], utils.Autograph(*["https://127.0.0.3", "hawk_user", "hawk_secret", ["autograph_marsha384"]])), (["invalid"], None)),
)
def test_get_autograph_config(context, formats, expected):
    assert sign.get_autograph_config(context.autograph_configs, TEST_CERT_TYPE, formats) == expected


def test_get_autograph_config_raises_signingscript_error(context):
    with pytest.raises(SigningScriptError):
        sign.get_autograph_config(context.autograph_configs, TEST_CERT_TYPE, signing_formats=["invalid"], raise_on_empty=True)


# sign_file {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize("to,expected", ((None, "from"), ("to", "to")))
async def test_sign_file_autograph(context, mocker, to, expected):
    context.task = {"scopes": ["project:releng:signing:cert:dep-signing"]}
    context.autograph_configs = {
        "project:releng:signing:cert:dep-signing": [
            utils.Autograph(*["https://autograph-hsm.dev.mozaws.net", "alice", "fs5wgcer9qj819kfptdlp8gm227ewxnzvsuj9ztycsx08hfhzu", ["autograph_mar"]])
        ]
    }
    mocker.patch.object(sign, "sign_file_with_autograph", new=noop_async)

    assert await sign.sign_file(context, "from", "autograph_mar", to=to) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "to,expected,format,options",
    (
        (None, "from", "autograph_mar", None),
        ("to", "to", "autograph_mar", None),
        ("to", "to", "autograph_apk_foo", {"zip": "passthrough"}),
        ("to", "to", "autograph_apk_sha1", {"pkcs7_digest": "SHA1", "zip": "passthrough"}),
    ),
)
async def test_sign_file_with_autograph(context, mocker, to, expected, format, options):
    open_mock = mocker.mock_open(read_data=b"0xdeadbeef")
    mocker.patch("builtins.open", open_mock, create=True)

    mocked_session = MockedSession(signed_file="bW96aWxsYQ==")
    mocker.patch.object(context, "session", new=mocked_session)

    context.task = {"scopes": ["project:releng:signing:cert:dep-signing"]}
    context.autograph_configs = {
        "project:releng:signing:cert:dep-signing": [
            utils.Autograph(*["https://autograph-hsm.dev.mozaws.net", "alice", "fs5wgcer9qj819kfptdlp8gm227ewxnzvsuj9ztycsx08hfhzu", [format]])
        ]
    }
    assert await sign.sign_file_with_autograph(context, "from", format, to=to) == expected
    open_mock.assert_called()
    kwargs = {"input": "MHhkZWFkYmVlZg=="}
    if options:
        kwargs["options"] = options
    mocked_session.post.assert_called_with("https://autograph-hsm.dev.mozaws.net/sign/file", headers=mocker.ANY, data=mocker.ANY)
    data = mocked_session.post.call_args[1]["data"]
    data.seek(0)
    assert json.load(data) == [kwargs]


@pytest.mark.asyncio
@pytest.mark.parametrize("to,expected", ((None, "from"), ("to", "to")))
async def test_sign_file_with_autograph_invalid_format_errors(context, mocker, to, expected):
    context.task = {"scopes": ["project:releng:signing:cert:dep-signing"]}
    context.autograph_configs = {}
    with pytest.raises(SigningScriptError):
        await sign.sign_file_with_autograph(context, "from", "mar", to=to)


@pytest.mark.asyncio
@pytest.mark.parametrize("to,expected", ((None, "from"), ("to", "to")))
async def test_sign_file_with_autograph_no_suitable_servers_errors(context, mocker, to, expected):
    context.task = {"scopes": ["project:releng:signing:cert:dep-signing"]}
    context.autograph_configs = {}
    with pytest.raises(SigningScriptError):
        await sign.sign_file_with_autograph(context, "from", "autograph_mar", to=to)


@pytest.mark.asyncio
@pytest.mark.parametrize("to,expected", ((None, "from"), ("to", "to")))
async def test_sign_file_with_autograph_raises_http_error(context, mocker, to, expected):
    open_mock = mocker.mock_open(read_data=b"0xdeadbeef")
    mocker.patch("builtins.open", open_mock, create=True)

    mocked_session = MockedSession(signed_file="bW96aWxsYQ==", exception=aiohttp.ClientError)
    mocker.patch.object(context, "session", new=mocked_session)

    async def fake_retry_async(func, args=(), attempts=5, sleeptime_kwargs=None):
        await func(*args)

    mocker.patch.object(sign, "retry_async", new=fake_retry_async)

    context.task = {"scopes": ["project:releng:signing:cert:dep-signing"]}
    context.autograph_configs = {
        "project:releng:signing:cert:dep-signing": [
            utils.Autograph(*["https://autograph-hsm.dev.mozaws.net", "alice", "fs5wgcer9qj819kfptdlp8gm227ewxnzvsuj9ztycsx08hfhzu", ["autograph_mar"]])
        ]
    }
    with pytest.raises(aiohttp.ClientError):
        await sign.sign_file_with_autograph(context, "from", "autograph_mar", to=to)
    open_mock.assert_called()


# get_mar_verification_key {{{1
@pytest.mark.parametrize(
    "format,cert_type,keyid,raises,expected",
    (
        ("autograph_stage_mar384", "dep-signing", None, False, os.path.join(INSTALL_DIR, "data", "autograph_stage.pem")),
        ("autograph_hash_only_mar384", "release-signing", None, False, os.path.join(INSTALL_DIR, "data", "release_primary.pem")),
        ("autograph_hash_only_mar384", "unknown_cert_type", None, True, None),
        ("unknown_format", "dep", None, True, None),
        ("autograph_hash_only_mar384", "release-signing", "firefox_20190321_rel", False, os.path.join(INSTALL_DIR, "data", "firefox_20190321_rel.pem")),
        ("autograph_hash_only_mar384", "release-signing", "../firefox_20190321_rel", True, None),
    ),
)
def test_get_mar_verification_key(format, cert_type, keyid, raises, expected):
    if raises:
        with pytest.raises(SigningScriptError):
            sign.get_mar_verification_key(cert_type, format, keyid)
    else:
        assert sign.get_mar_verification_key(cert_type, format, keyid) == expected


# verify_mar_signature {{{1
@pytest.mark.parametrize("raises", (True, False))
def test_verify_mar_signature(mocker, raises):
    def fake_check_call(*args, **kwargs):
        if raises:
            raise subprocess.CalledProcessError("x", "foo")

    mocker.patch.object(subprocess, "check_call", new=fake_check_call)
    if raises:
        with pytest.raises(SigningScriptError):
            sign.verify_mar_signature("dep-signing", "autograph_stage_mar384", "foo")
    else:
        sign.verify_mar_signature("dep-signing", "autograph_stage_mar384", "foo")


# sign_mar384_with_autograph_hash {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize("to,expected", ((None, "from"), ("to", "to")))
async def test_sign_mar384_with_autograph_hash(context, mocker, to, expected):
    open_mock = mocker.mock_open(read_data=b"0xdeadbeef")
    mocker.patch("builtins.open", open_mock, create=True)

    mocked_session = MockedSession(signature=base64.b64encode(b"0" * 512))
    mocker.patch.object(context, "session", new=mocked_session)

    add_signature_mock = mocker.Mock()
    mocker.patch("signingscript.sign.add_signature_block", add_signature_mock, create=True)

    m_mock = mocker.MagicMock()
    m_mock.calculate_hashes.return_value = [[None, b"b64marhash"]]
    MarReader_mock = mocker.Mock()
    MarReader_mock.return_value.__enter__ = mocker.Mock(return_value=m_mock)
    MarReader_mock.return_value.__exit__ = mocker.Mock()
    mocker.patch("signingscript.sign.MarReader", MarReader_mock, create=True)
    mocker.patch("signingscript.sign.verify_mar_signature")

    context.task = {"scopes": ["project:releng:signing:cert:dep-signing"]}
    context.autograph_configs = {
        "project:releng:signing:cert:dep-signing": [
            utils.Autograph(
                "https://autograph-hsm.dev.mozaws.net", "alice", "fs5wgcer9qj819kfptdlp8gm227ewxnzvsuj9ztycsx08hfhzu", ["autograph_hash_only_mar384"]
            )
        ]
    }
    assert await sign.sign_mar384_with_autograph_hash(context, "from", "autograph_hash_only_mar384", to=to) == expected
    open_mock.assert_called()
    add_signature_mock.assert_called()
    MarReader_mock.assert_called()
    m_mock.calculate_hashes.assert_called()
    mocked_session.post.assert_called_with("https://autograph-hsm.dev.mozaws.net/sign/hash", headers=mocker.ANY, data=mocker.ANY)
    assert json.load(mocked_session.post.call_args[1]["data"]) == [{"input": "YjY0bWFyaGFzaA=="}]


@pytest.mark.asyncio
async def test_sign_mar384_with_autograph_hash_keyid(context, mocker):
    context.task = {"scopes": ["project:releng:signing:cert:dep-signing"]}
    context.autograph_configs = {
        "project:releng:signing:cert:dep-signing": [
            utils.Autograph(
                "https://autograph-hsm.dev.mozaws.net",
                "alice",
                "fs5wgcer9qj819kfptdlp8gm227ewxnzvsuj9ztycsx08hfhzu",
                ["autograph_hash_only_mar384"],
                "autograph",
            )
        ]
    }

    open_mock = mocker.mock_open(read_data=b"0xdeadbeef")
    mocker.patch("builtins.open", open_mock, create=True)
    mocker.patch("signingscript.sign.add_signature_block")
    mar_reader = mocker.patch("signingscript.sign.MarReader")
    mar_reader.calculate_hashes.return_value = [[None, b"b64marhash"]]
    mocker.patch("signingscript.sign.verify_mar_signature")

    async def fake_sign_hash(context, h, fmt, keyid):
        return b"#" * 512

    fake_sign_hash = mock.MagicMock(wraps=fake_sign_hash)
    mocker.patch("signingscript.sign.sign_hash_with_autograph", fake_sign_hash)

    assert await sign.sign_mar384_with_autograph_hash(context, "from", "autograph_hash_only_mar384:keyid1") == "from"
    fake_sign_hash.assert_called_with(mocker.ANY, mocker.ANY, "autograph_hash_only_mar384", "keyid1")


@pytest.mark.asyncio
@pytest.mark.parametrize("to,expected", ((None, "from"), ("to", "to")))
async def test_sign_mar384_with_autograph_hash_invalid_format_errors(context, mocker, to, expected):
    context.task = {"scopes": ["project:releng:signing:cert:dep-signing"]}
    context.autograph_configs = {}
    with pytest.raises(SigningScriptError):
        await sign.sign_mar384_with_autograph_hash(context, "from", "mar", to=to)


@pytest.mark.asyncio
@pytest.mark.parametrize("to,expected", ((None, "from"), ("to", "to")))
async def test_sign_mar384_with_autograph_hash_no_suitable_servers_errors(context, mocker, to, expected):
    context.task = {"scopes": ["project:releng:signing:cert:dep-signing"]}
    context.autograph_configs = {}
    with pytest.raises(SigningScriptError):
        await sign.sign_mar384_with_autograph_hash(context, "from", "autograph_hash_only_mar384", to=to)


@pytest.mark.asyncio
@pytest.mark.parametrize("to,expected", ((None, "from"), ("to", "to")))
async def test_sign_mar384_with_autograph_hash_returns_invalid_signature_length(context, mocker, to, expected):
    open_mock = mocker.mock_open(read_data=b"0xdeadbeef")
    mocker.patch("builtins.open", open_mock, create=True)

    mocked_session = MockedSession(signature=base64.b64encode(b"0"))
    mocker.patch.object(context, "session", new=mocked_session)

    add_signature_mock = mocker.Mock()
    mocker.patch("signingscript.sign.add_signature_block", add_signature_mock, create=True)

    m_mock = mocker.MagicMock()
    m_mock.calculate_hashes.return_value = [[None, b"b64marhash"]]
    MarReader_mock = mocker.Mock()
    MarReader_mock.return_value.__enter__ = mocker.Mock(return_value=m_mock)
    MarReader_mock.return_value.__exit__ = mocker.Mock()
    mocker.patch("signingscript.sign.MarReader", MarReader_mock, create=True)

    context.task = {"scopes": ["project:releng:signing:cert:dep-signing"]}
    context.autograph_configs = {
        "project:releng:signing:cert:dep-signing": [
            utils.Autograph(
                "https://autograph-hsm.dev.mozaws.net", "alice", "fs5wgcer9qj819kfptdlp8gm227ewxnzvsuj9ztycsx08hfhzu", ["autograph_hash_only_mar384"]
            )
        ]
    }
    with pytest.raises(SigningScriptError):
        assert await sign.sign_mar384_with_autograph_hash(context, "from", "autograph_hash_only_mar384", to=to) == expected

    open_mock.assert_called()
    add_signature_mock.assert_called()
    MarReader_mock.assert_called()
    m_mock.calculate_hashes.assert_called()
    mocked_session.post.assert_called_with("https://autograph-hsm.dev.mozaws.net/sign/hash", headers=mocker.ANY, data=mocker.ANY)
    assert json.load(mocked_session.post.call_args[1]["data"]) == [{"input": "YjY0bWFyaGFzaA=="}]


# sign_gpg {{{1
@pytest.mark.asyncio
async def test_sign_gpg(context, mocker):
    mocker.patch.object(sign, "sign_file", new=noop_async)
    assert await sign.sign_gpg(context, "from", "blah") == ["from", "from.asc"]


# sign_jar {{{1
@pytest.mark.asyncio
async def test_sign_jar(context, mocker):
    counter = []

    async def fake_zipalign(*args):
        counter.append("1")

    mocker.patch.object(sign, "sign_file", new=noop_async)
    mocker.patch.object(sign, "zip_align_apk", new=fake_zipalign)
    await sign.sign_jar(context, "from", "blah")
    assert len(counter) == 1


# sign_macapp {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize("filename,expected", (("foo.dmg", "foo.tar.gz"), ("foo.tar.bz2", "foo.tar.bz2")))
async def test_sign_macapp(context, mocker, filename, expected):
    mocker.patch.object(sign, "_convert_dmg_to_tar_gz", new=noop_async)
    mocker.patch.object(sign, "sign_file", new=noop_async)
    assert await sign.sign_macapp(context, filename, "blah") == expected


# sign_xpi {{{1
@pytest.mark.parametrize("fmt, is_xpi", (("foo_omnija", True), ("langpack_foo", True), ("privileged_webextension", True), ("unknown", False)))
def test_is_xpi_format(fmt, is_xpi):
    assert sign._is_xpi_format(fmt) is is_xpi


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename,id,raises",
    (
        ("foo.blah", "foo-id@firefox.mozilla.org", pytest.raises(SigningScriptError)),
        ("/path/to/foo.xpi", "foo-id@firefox.mozilla.org", does_not_raise()),
        ("foo.xpi", "foo-id@devedition.mozilla.org", does_not_raise()),
    ),
)
async def test_sign_xpi(context, mocker, filename, id, raises):
    async def mocked_signer(ctx, fname, fmt, extension_id=None):
        assert extension_id == id

    context.task = {"scopes": ["project:releng:signing:cert:dep-signing"]}

    mocker.patch.object(sign, "get_autograph_config")
    mocker.patch.object(sign, "_extension_id", return_value=id)
    mocker.patch.object(sign, "_extension_id", return_value=id)
    mocker.patch.object(sign, "sign_file_with_autograph", new=mocked_signer)
    with raises:
        assert await sign.sign_xpi(context, filename, "autograph_langpack") == filename


# sign_widevine {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename,fmt,raises,should_sign,orig_files",
    (
        ("foo.tar.gz", "widevine", False, True, None),
        ("foo.zip", "widevine_blessed", False, True, None),
        (
            "foo.dmg",
            "widevine",
            False,
            True,
            ["foo.app/Contents/MacOS/firefox", "foo.app/Contents/MacOS/bar.app/Contents/MacOS/plugin-container", "foo.app/ignore"],
        ),
        ("foo.unknown", "widevine", True, False, None),
        ("foo.zip", "widevine", False, False, None),
        ("foo.dmg", "widevine", False, False, None),
        ("foo.tar.bz2", "widevine", False, False, None),
        ("foo.zip", "autograph_widevine", False, True, None),
        ("foo.dmg", "autograph_widevine", False, True, None),
        ("foo.tar.bz2", "autograph_widevine", False, True, None),
    ),
)
async def test_sign_widevine(context, mocker, filename, fmt, raises, should_sign, orig_files):
    if should_sign:
        files = orig_files or ["isdir/firefox", "firefox/firefox", "y/plugin-container", "z/blah", "ignore"]
    else:
        files = orig_files or ["z/blah", "ignore"]

    async def fake_filelist(*args, **kwargs):
        return files

    async def fake_unzip(_, f, **kwargs):
        assert f.endswith(".zip")
        return files

    async def fake_untar(_, f, comp, **kwargs):
        assert f.endswith(".tar.{}".format(comp.lstrip(".")))
        return files

    async def fake_undmg(_, f):
        assert f.endswith(".dmg")

    async def fake_sign(_, f, fmt, **kwargs):
        if f.endswith("firefox"):
            assert fmt == "widevine"
        elif f.endswith("container"):
            assert fmt == "widevine_blessed"
        else:
            assert False, "unexpected file and format {} {}!".format(f, fmt)
        if "MacOS" in f:
            assert f not in files, "We should have renamed this file!"

    def fake_isfile(path):
        return "isdir" not in path

    mocker.patch.object(sign, "_get_tarfile_files", new=fake_filelist)
    mocker.patch.object(sign, "_extract_tarfile", new=fake_untar)
    mocker.patch.object(sign, "_get_zipfile_files", new=fake_filelist)
    mocker.patch.object(sign, "_extract_zipfile", new=fake_unzip)
    mocker.patch.object(sign, "_convert_dmg_to_tar_gz", new=fake_undmg)
    mocker.patch.object(sign, "sign_file", new=noop_async)
    mocker.patch.object(sign, "sign_widevine_with_autograph", new=noop_async)
    mocker.patch.object(sign, "makedirs", new=noop_sync)
    mocker.patch.object(sign, "generate_precomplete", new=noop_sync)
    mocker.patch.object(sign, "_create_tarfile", new=noop_async)
    mocker.patch.object(sign, "_create_zipfile", new=noop_async)
    mocker.patch.object(sign, "_run_generate_precomplete", new=noop_sync)
    mocker.patch.object(os.path, "isfile", new=fake_isfile)

    if raises:
        with pytest.raises(SigningScriptError):
            await sign.sign_widevine(context, filename, fmt)
    else:
        await sign.sign_widevine(context, filename, fmt)


# _should_sign_windows {{{1
@pytest.mark.parametrize(
    "filenames,expected", ((("firefox", "libclearkey.dylib", "D3DCompiler_42.dll", "msvcblah.dll"), False), (("firefox.dll", "foo.exe"), True))
)
def test_should_sign_windows(filenames, expected):
    for f in filenames:
        assert sign._should_sign_windows(f) == expected


# _get_widevine_signing_files {{{1
@pytest.mark.parametrize(
    "filenames,expected",
    (
        (["firefox.dll", "XUL.so", "firefox.bin", "blah"], {}),
        (
            ("firefox", "blah/XUL", "foo/bar/libclearkey.dylib", "baz/plugin-container", "ignore"),
            {"firefox": "widevine", "blah/XUL": "widevine", "foo/bar/libclearkey.dylib": "widevine", "baz/plugin-container": "widevine_blessed"},
        ),
        (
            # Test for existing signature files
            (
                "firefox",
                "blah/XUL",
                "blah/XUL.sig",
                "foo/bar/libclearkey.dylib",
                "foo/bar/libclearkey.dylib.sig",
                "plugin-container",
                "plugin-container.sig",
                "ignore",
            ),
            {"firefox": "widevine"},
        ),
    ),
)
def test_get_widevine_signing_files(filenames, expected):
    assert sign._get_widevine_signing_files(filenames) == expected


# _run_generate_precomplete {{{1
@pytest.mark.parametrize("num_precomplete,raises", ((1, False), (0, True), (2, True)))
def test_run_generate_precomplete(context, num_precomplete, raises, mocker):
    mocker.patch.object(sign, "generate_precomplete", new=noop_sync)
    work_dir = context.config["work_dir"]
    for i in range(0, num_precomplete):
        path = os.path.join(work_dir, "foo", str(i))
        makedirs(path)
        with open(os.path.join(path, "precomplete"), "w") as fh:
            fh.write("blah")
    if raises:
        with pytest.raises(SigningScriptError):
            sign._run_generate_precomplete(context, work_dir)
    else:
        sign._run_generate_precomplete(context, work_dir)


# remove_extra_files {{{1
def test_remove_extra_files(context):
    extra = ["a", "b/c"]
    good = ["d", "e/f"]
    work_dir = context.config["work_dir"]
    all_files = []
    for f in extra + good:
        path = os.path.join(work_dir, f)
        makedirs(os.path.dirname(path))
        with open(path, "w") as fh:
            fh.write("x")
        if f in good:
            all_files.append(path)
    for f in good:
        assert os.path.exists(os.path.join(work_dir, f))
    output = sign.remove_extra_files(work_dir, all_files)
    for f in extra:
        path = os.path.realpath(os.path.join(work_dir, f))
        assert path in output
        assert not os.path.exists(path)
    for f in good:
        assert os.path.exists(os.path.join(work_dir, f))


# zip_align_apk {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize("is_verbose", (True, False))
async def test_zip_align_apk(context, monkeypatch, is_verbose):
    context.config["zipalign"] = "/path/to/android/sdk/zipalign"
    context.config["verbose"] = is_verbose
    abs_to = "/absolute/path/to/apk.apk"

    async def execute_subprocess_mock(command):
        if is_verbose:
            assert command[0:4] == ["/path/to/android/sdk/zipalign", "-v", "4", abs_to]
            assert len(command) == 5
        else:
            assert command[0:3] == ["/path/to/android/sdk/zipalign", "4", abs_to]
            assert len(command) == 4

    def shutil_mock(_, destination):
        assert destination == abs_to

    monkeypatch.setattr("signingscript.utils.execute_subprocess", execute_subprocess_mock)
    monkeypatch.setattr("shutil.move", shutil_mock)

    await sign.zip_align_apk(context, abs_to)


# _convert_dmg_to_tar_gz {{{1
@pytest.mark.asyncio
async def test_convert_dmg_to_tar_gz(context, monkeypatch, tmpdir):
    dmg_path = "path/to/foo.dmg"
    abs_dmg_path = os.path.join(context.config["work_dir"], dmg_path)
    tarball_path = "path/to/foo.tar.gz"
    abs_tarball_path = os.path.join(context.config["work_dir"], tarball_path)

    async def execute_subprocess_mock(command, **kwargs):
        assert command in (
            ["dmg", "extract", abs_dmg_path, "tmp.hfs"],
            ["hfsplus", "tmp.hfs", "extractall", "/", "{}/app".format(tmpdir)],
            ["tar", "czf", abs_tarball_path, "."],
        )

    @contextmanager
    def fake_tmpdir():
        yield tmpdir

    monkeypatch.setattr("signingscript.utils.execute_subprocess", execute_subprocess_mock)
    monkeypatch.setattr("tempfile.TemporaryDirectory", fake_tmpdir)

    await sign._convert_dmg_to_tar_gz(context, dmg_path)


# _extract_zipfile _create_zipfile {{{1
@pytest.mark.asyncio
async def test_get_zipfile_files():
    assert sorted(await sign._get_zipfile_files(os.path.join(TEST_DATA_DIR, "test.zip"))) == ["a", "b", "c/", "c/d", "c/e/", "c/e/f"]


@pytest.mark.asyncio
async def test_working_zipfile(context):
    await helper_archive(context, "foo.zip", sign._create_zipfile, sign._extract_zipfile)
    files = ["c/d", "c/e/f"]
    tmp_dir = os.path.join(context.config["work_dir"], "foo")
    expected = [os.path.join(tmp_dir, f) for f in files]
    assert await sign._extract_zipfile(context, os.path.join(TEST_DATA_DIR, "test.zip"), files=files, tmp_dir=tmp_dir) == expected
    for f in expected:
        assert os.path.exists(f)


@pytest.mark.asyncio
async def test_bad_create_zipfile(context, mocker):
    mocker.patch.object(zipfile, "ZipFile", new=context_die)
    with pytest.raises(SigningScriptError):
        await sign._create_zipfile(context, "foo.zip", [])


@pytest.mark.asyncio
async def test_bad_extract_zipfile(context, mocker):
    mocker.patch.object(sign, "rm", new=die)
    with pytest.raises(SigningScriptError):
        await sign._extract_zipfile(context, "foo.zip")


@pytest.mark.asyncio
async def test_zipfile_append_write(context):
    top_dir = os.path.dirname(os.path.dirname(__file__))
    rel_files = ["tests/test_script.py", "tests/test_sign.py"]
    abs_files = [os.path.join(top_dir, f) for f in rel_files]
    full_rel_files = ["a", "b", "c/", "c/d", "c/e/", "c/e/f"] + rel_files
    to = os.path.join(context.config["work_dir"], "test.zip")

    # mode='w' -- zipfile should only have these two files
    shutil.copyfile(os.path.join(TEST_DATA_DIR, "test.zip"), to)
    await sign._create_zipfile(context, to, abs_files, tmp_dir=top_dir, mode="w")
    assert sorted(await sign._get_zipfile_files(to)) == rel_files

    # mode='a' -- zipfile should have previous files + new files
    shutil.copyfile(os.path.join(TEST_DATA_DIR, "test.zip"), to)
    await sign._create_zipfile(context, to, abs_files, tmp_dir=top_dir, mode="a")
    assert sorted(await sign._get_zipfile_files(to)) == full_rel_files


# tarfile {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize("path,compression", ((os.path.join(TEST_DATA_DIR, "test.tar.bz2"), "bz2"), (os.path.join(TEST_DATA_DIR, "test.tar.gz"), "gz")))
async def test_get_tarfile_files(path, compression):
    assert sorted(await sign._get_tarfile_files(path, compression)) == ["./a", "./b", "./c/d", "./c/e/f"]


@pytest.mark.parametrize("compression,expected,raises", ((".gz", "gz", False), ("bz2", "bz2", False), ("superstrong_compression!!!", None, True)))
def test_get_tarfile_compression(compression, expected, raises):
    if raises:
        with pytest.raises(SigningScriptError):
            sign._get_tarfile_compression(compression)
    else:
        assert sign._get_tarfile_compression(compression) == expected


@pytest.mark.asyncio
async def test_working_tarfile(context):
    await helper_archive(context, "foo.tar.gz", sign._create_tarfile, sign._extract_tarfile, "gz")


@pytest.mark.asyncio
async def test_bad_create_tarfile(context, mocker):
    mocker.patch.object(tarfile, "open", new=context_die)
    with pytest.raises(SigningScriptError):
        await sign._create_tarfile(context, "foo.tar.gz", [], ".bz2")


@pytest.mark.asyncio
async def test_bad_extract_tarfile(context, mocker):
    mocker.patch.object(tarfile, "open", new=context_die)
    with pytest.raises(SigningScriptError):
        await sign._extract_tarfile(context, "foo.tar.gz", "gz")


@pytest.mark.asyncio
async def test_tarfile_append_write(context):
    top_dir = os.path.dirname(os.path.dirname(__file__))
    rel_files = ["tests/test_script.py", "tests/test_sign.py"]
    abs_files = [os.path.join(top_dir, f) for f in rel_files]
    to = os.path.join(context.config["work_dir"], "test.tar.bz2")

    # mode='w' -- tarfile should only have these two files
    shutil.copyfile(os.path.join(TEST_DATA_DIR, "test.tar.bz2"), to)
    await sign._create_tarfile(context, to, abs_files, "bz2", tmp_dir=top_dir)
    assert sorted(await sign._get_tarfile_files(to, "bz2")) == rel_files


def test_signreq_task_keyid():
    fmt = "autograph_hash_only_mar384"
    req = sign.make_signing_req(None, fmt, "newkeyid")

    assert req["keyid"] == "newkeyid"
    assert req["input"] is None


def test_signreq_task_omnija():
    fmt = "autograph_omnija"
    req = sign.make_signing_req(None, fmt, "newkeyid", extension_id="omni.ja@mozilla.org")

    assert req["keyid"] == "newkeyid"
    assert req["input"] is None
    assert req["options"]["id"] == "omni.ja@mozilla.org"
    assert isinstance(req["options"]["cose_algorithms"], type([]))
    assert len(req["options"]["cose_algorithms"]) == 1
    assert req["options"]["cose_algorithms"][0] == "ES256"
    assert req["options"]["pkcs7_digest"] == "SHA256"


def test_signreq_task_langpack():
    fmt = "autograph_langpack"
    req = sign.make_signing_req(None, fmt, "newkeyid", extension_id="langpack-en-CA@firefox.mozilla.org")

    assert req["keyid"] == "newkeyid"
    assert req["input"] is None
    assert req["options"]["id"] == "langpack-en-CA@firefox.mozilla.org"
    assert isinstance(req["options"]["cose_algorithms"], type([]))
    assert len(req["options"]["cose_algorithms"]) == 1
    assert req["options"]["cose_algorithms"][0] == "ES256"
    assert req["options"]["pkcs7_digest"] == "SHA256"


@pytest.mark.asyncio
async def test_bad_autograph_method():
    with pytest.raises(SigningScriptError):
        await sign.sign_with_autograph(None, None, None, None, "gpg")


@pytest.mark.asyncio
async def test_bad_autograph_format(context):
    context.task = {"scopes": ["project:releng:signing:cert:dep-signing"]}
    with pytest.raises(SigningScriptError):
        await sign.sign_file_with_autograph(context, "", "gpg")

    with pytest.raises(SigningScriptError):
        await sign.sign_hash_with_autograph(context, "", "gpg")


@pytest.mark.asyncio
@pytest.mark.parametrize("blessed", (True, False))
async def test_widevine_autograph(context, mocker, tmp_path, blessed):
    wv = mocker.patch("signingscript.sign.widevine")
    wv.generate_widevine_hash.return_value = b"hashhashash"
    wv.generate_widevine_signature.return_value = b"sigwidevinesig"
    called_format = None

    async def fake_sign_hash(context, h, fmt):
        nonlocal called_format
        called_format = fmt
        return b"sigautographsig"

    mocker.patch("signingscript.sign.sign_hash_with_autograph", fake_sign_hash)

    cert = tmp_path / "widevine.crt"
    cert.write_bytes(b"TMPCERT")
    context.config["widevine_cert"] = cert

    to = tmp_path / "signed.sig"
    to = await sign.sign_widevine_with_autograph(context, "from", blessed, to=to)

    assert b"sigwidevinesig" == to.read_bytes()
    assert called_format == "autograph_widevine"


@pytest.mark.asyncio
async def test_no_widevine(context, mocker, tmp_path):
    async def fake_sign_hash(*args, **kwargs):
        return b"sigautographsig"

    mocker.patch("signingscript.sign.sign_hash_with_autograph", fake_sign_hash)

    with pytest.raises(ImportError):
        to = tmp_path / "signed.sig"
        to = await sign.sign_widevine_with_autograph(context, "from", True, to=to)


@pytest.mark.asyncio
async def test_gpg_autograph(context, mocker, tmp_path):
    tmp = tmp_path / "file.txt"
    tmp.write_text("hello world")

    context.task = {"scopes": ["project:releng:signing:cert:dep-signing"]}
    context.autograph_configs = {
        "project:releng:signing:cert:dep-signing": [
            utils.Autograph("https://autograph-hsm.dev.mozaws.net", "alice", "fs5wgcer9qj819kfptdlp8gm227ewxnzvsuj9ztycsx08hfhzu", ["autograph_gpg"])
        ]
    }

    mocked_sign = mocker.patch.object(sign, "sign_with_autograph")
    mocked_sign.return_value = async_mock_return_value("--- FAKE SIG ---")

    result = await sign.sign_gpg_with_autograph(context, tmp, "autograph_gpg")

    assert result == [tmp, f"{tmp}.asc"]

    with pytest.raises(SigningScriptError):
        result = await sign.sign_gpg_with_autograph(context, tmp, "gpg")


# sign_omnija {{{1  -- 537
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename,raises,nofiles",
    (
        ("foo.unknown", True, False),
        ("foo.zip", False, False),
        ("foo.dmg", False, False),
        ("foo.tar.bz2", False, False),
        ("foo.zip", False, True),
        ("foo.dmg", False, True),
        ("foo.tar.bz2", False, True),
    ),
)
async def test_sign_omnija(context, mocker, filename, raises, nofiles):
    fmt = "autograph_omnija"
    files = ["isdir/omni.ja", "firefox/omni.ja", "firefox/browser/omni.ja", "z/blah", "ignore"]
    if nofiles:
        # Don't have any omni.ja
        files = ["z/blah", "ignore"]

    async def fake_filelist(*args, **kwargs):
        return files

    async def fake_unzip(_, f, **kwargs):
        assert f.endswith(".zip")
        return files

    async def fake_untar(_, f, comp, **kwargs):
        assert f.endswith(".tar.{}".format(comp.lstrip(".")))
        return files

    async def fake_undmg(_, f):
        assert f.endswith(".dmg")

    def fake_isfile(path):
        return "isdir" not in path

    mocker.patch.object(sign, "_get_tarfile_files", new=fake_filelist)
    mocker.patch.object(sign, "_extract_tarfile", new=fake_untar)
    mocker.patch.object(sign, "_get_zipfile_files", new=fake_filelist)
    mocker.patch.object(sign, "_extract_zipfile", new=fake_unzip)
    mocker.patch.object(sign, "_convert_dmg_to_tar_gz", new=fake_undmg)
    mocker.patch.object(sign, "sign_omnija_with_autograph", new=noop_async)
    mocker.patch.object(sign, "_create_tarfile", new=noop_async)
    mocker.patch.object(sign, "_create_zipfile", new=noop_async)
    mocker.patch.object(os.path, "isfile", new=fake_isfile)

    if raises:
        with pytest.raises(SigningScriptError):
            await sign.sign_omnija(context, filename, fmt)
    else:
        await sign.sign_omnija(context, filename, fmt)


# _get_omnija_signing_files {{{1  -- 621
@pytest.mark.parametrize(
    "filenames,expected",
    (
        (["firefox.dll", "XUL.so", "firefox.bin", "blah"], {}),
        (("firefox", "blah/omni.ja", "foo/bar/libclearkey.dylib", "baz/omni.ja", "ignore"), {"blah/omni.ja": "omnija", "baz/omni.ja": "omnija"}),
    ),
)
def test_get_omnija_signing_files(filenames, expected):
    assert sign._get_omnija_signing_files(filenames) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("orig", ("no_preload_unsigned_omni.ja", "preload_unsigned_omni.ja"))
async def test_omnija_same(mocker, tmpdir, orig):
    copy_from = os.path.join(tmpdir, "omni.ja")
    shutil.copyfile(os.path.join(TEST_DATA_DIR, orig), copy_from)
    copy_to = os.path.join(tmpdir, "new_omni.ja")

    class mockedZipFile(object):
        def __init__(self, name, mode, *args, **kwargs):
            assert name == "signed.ja"
            assert mode == "r"

        def namelist(self):
            return ["foobar", "baseball"]

    mocker.patch.object(sign.zipfile, "ZipFile", mockedZipFile)
    await sign.merge_omnija_files(copy_from, "signed.ja", copy_to)
    assert open(copy_from, "rb").read() == open(copy_to, "rb").read()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "orig,signed,sha256_expected",
    (
        ("no_preload_unsigned_omni.ja", "no_preload_signed_omni.ja", "851890c7eac926ad1dfd1fc4b7bf96e57b519d87806f1055fe108d493e753f98"),
        ("preload_unsigned_omni.ja", "preload_signed_omni.ja", "d619ab6c25b31950540847b520d0791625ab4ca31ee4f58d02409c784f9206cd"),
    ),
)
async def test_omnija_sign(tmpdir, mocker, context, orig, signed, sha256_expected):
    copy_from = os.path.join(tmpdir, "omni.ja")
    shutil.copyfile(os.path.join(TEST_DATA_DIR, orig), copy_from)

    async def mocked_autograph(context, from_, fmt, to, extension_id):
        assert fmt == "autograph_omnija"
        shutil.copyfile(os.path.join(TEST_DATA_DIR, signed), to)

    mocker.patch.object(sign, "sign_file_with_autograph", mocked_autograph)
    await sign.sign_omnija_with_autograph(context, copy_from)
    sha256_actual = sha256(open(copy_from, "rb").read()).hexdigest()
    assert sha256_actual == sha256_expected


def test_langpack_id_regex():
    assert sign.LANGPACK_RE.match("langpack-en-CA@firefox.mozilla.org") is not None
    assert sign.LANGPACK_RE.match("langpack-ja-JP-mac@devedition.mozilla.org") is not None
    assert sign.LANGPACK_RE.match("invalid-langpack-id@example.com") is None


def test_extension_id():
    filename = os.path.join(TEST_DATA_DIR, "en-CA.xpi")
    assert sign._extension_id(filename, "autograph_langpack") == "langpack-en-CA@firefox.mozilla.org"


def test_extension_id_missing_manifest():
    filename = os.path.join(TEST_DATA_DIR, "test.zip")
    with pytest.raises(SigningScriptError):
        sign._extension_id(filename, "autograph_langpack")


@pytest.mark.parametrize(
    "json_,raises",
    (
        ({}, pytest.raises(SigningScriptError)),
        ({"languages": {}}, pytest.raises(SigningScriptError)),
        ({"languages": {}, "langpack_id": "en-CA"}, pytest.raises(SigningScriptError)),
        ({"languages": {}, "langpack_id": "en-CA", "applications": {}}, pytest.raises(SigningScriptError)),
        ({"languages": {}, "langpack_id": "en-CA", "applications": {"gecko": {}}}, pytest.raises(SigningScriptError)),
        ({"languages": {}, "langpack_id": "en-CA", "applications": {"gecko": {}}}, pytest.raises(SigningScriptError)),
        ({"languages": {}, "langpack_id": "en-CA", "applications": {"gecko": {"id": ""}}}, pytest.raises(SigningScriptError)),
        ({"languages": {}, "langpack_id": "en-CA", "applications": {"gecko": {"id": "invalid-langpack-id@example.com"}}}, pytest.raises(SigningScriptError)),
        ({"languages": {}, "langpack_id": "en-CA", "applications": {"gecko": {"id": "langpack-en-CA@firefox.mozilla.org"}}}, does_not_raise()),
        ({"languages": {}, "langpack_id": "en-CA", "applications": {"gecko": {"id": "langpack-de@devedition.mozilla.org"}}}, does_not_raise()),
        ({"languages": {}, "langpack_id": "en-CA", "applications": {"gecko": {"id": "langpack-ja-JP-mac@devedition.mozilla.org"}}}, does_not_raise()),
        ({"langpack_id": "en-CA", "applications": {"gecko": {"id": "langpack-en-CA@firefox.mozilla.org"}}}, pytest.raises(SigningScriptError)),
    ),
)
def test_extension_id_raises(json_, raises, mocker):
    filename = os.path.join(TEST_DATA_DIR, "en-CA.xpi")

    def load_manifest(*args, **kwargs):
        return json_

    # Mock ZipFile so we don't actually read the xpi data
    mocker.patch.object(sign.zipfile, "ZipFile", autospec=True)

    mocker.patch.object(sign.json, "load", load_manifest)
    with raises:
        id = sign._extension_id(filename, "autograph_langpack")
        assert id == json_["applications"]["gecko"]["id"]


@pytest.mark.asyncio
@pytest.mark.parametrize("fmt", ("autograph_authenticode", "autograph_authenticode_stub"))
@pytest.mark.parametrize("use_comment", (True, False))
async def test_authenticode_sign_zip(tmpdir, mocker, context, fmt, use_comment):
    context.config["authenticode_cert"] = os.path.join(TEST_DATA_DIR, "windows.crt")
    context.config["authenticode_cross_cert"] = os.path.join(TEST_DATA_DIR, "windows.crt")
    context.config["authenticode_url"] = "https://example.com"
    context.config["authenticode_timestamp_style"] = None
    comment = None
    if use_comment:
        comment = "Some authenticode comment"

    test_file = os.path.join(tmpdir, "windows.zip")
    shutil.copyfile(os.path.join(TEST_DATA_DIR, "windows.zip"), test_file)

    async def mocked_autograph(context, from_, fmt, keyid):
        return b""

    async def mocked_winsign(infile, outfile, digest_algo, certs, signer, comment=None, **kwargs):
        if infile.endswith(".msi") and use_comment:
            assert comment == "Some authenticode comment"
        else:
            assert comment is None
        await signer("", "")
        shutil.copyfile(infile, outfile)
        return True

    def mocked_issigned(filename):
        if filename.endswith("signed.exe"):
            return True

    mocker.patch.object(winsign.sign, "sign_file", mocked_winsign)
    mocker.patch.object(winsign.osslsigncode, "is_signed", mocked_issigned)
    mocker.patch.object(sign, "sign_hash_with_autograph", mocked_autograph)

    result = await sign.sign_authenticode_zip(context, test_file, fmt, authenticode_comment=comment)
    assert result == test_file
    assert os.path.exists(result)


@pytest.mark.asyncio
@pytest.mark.parametrize("fmt", ("autograph_authenticode", "autograph_authenticode_stub"))
@pytest.mark.parametrize("use_comment", (True, False))
async def test_authenticode_sign_msi(tmpdir, mocker, context, fmt, use_comment):
    context.config["authenticode_cert"] = os.path.join(TEST_DATA_DIR, "windows.crt")
    context.config["authenticode_cross_cert"] = os.path.join(TEST_DATA_DIR, "windows.crt")
    context.config["authenticode_url"] = "https://example.com"
    context.config["authenticode_timestamp_style"] = None
    comment = None
    if use_comment:
        comment = "Some authenticode comment"

    test_file = os.path.join(tmpdir, "windows.msi")
    shutil.copyfile(os.path.join(TEST_DATA_DIR, "windows.zip"), test_file)

    async def mocked_autograph(context, from_, fmt, keyid):
        return b""

    async def mocked_winsign(infile, outfile, digest_algo, certs, signer, comment=None, **kwargs):
        assert digest_algo == "sha1"
        if not use_comment:
            assert comment is None
        else:
            assert comment == "Some authenticode comment"
        await signer("", "")
        shutil.copyfile(infile, outfile)
        return True

    def mocked_issigned(filename):
        if filename.endswith("signed.exe"):
            return True

    mocker.patch.object(winsign.sign, "sign_file", mocked_winsign)
    mocker.patch.object(winsign.osslsigncode, "is_signed", mocked_issigned)
    mocker.patch.object(sign, "sign_hash_with_autograph", mocked_autograph)

    result = await sign.sign_authenticode_zip(context, test_file, fmt, authenticode_comment=comment)
    assert result == test_file
    assert os.path.exists(result)


@pytest.mark.asyncio
async def test_authenticode_ev_sha(tmpdir, mocker, context):
    context.config["authenticode_cert"] = os.path.join(TEST_DATA_DIR, "windows.crt")
    context.config["authenticode_cross_cert"] = os.path.join(TEST_DATA_DIR, "windows.crt")
    context.config["authenticode_url"] = "https://example.com"
    context.config["authenticode_timestamp_style"] = None

    test_file = os.path.join(tmpdir, "windows.msi")
    shutil.copyfile(os.path.join(TEST_DATA_DIR, "windows.zip"), test_file)

    fmt = "authenticode_ev"

    async def mocked_autograph(context, from_, fmt, keyid):
        return b""

    async def mocked_winsign(infile, outfile, digest_algo, certs, signer, comment=None, **kwargs):
        assert digest_algo == "sha256"
        await signer("", "")
        shutil.copyfile(infile, outfile)
        return True

    def mocked_issigned(filename):
        if filename.endswith("signed.exe"):
            return True

    mocker.patch.object(winsign.sign, "sign_file", mocked_winsign)
    mocker.patch.object(winsign.osslsigncode, "is_signed", mocked_issigned)
    mocker.patch.object(sign, "sign_hash_with_autograph", mocked_autograph)

    result = await sign.sign_authenticode_zip(context, test_file, fmt)
    assert result == test_file
    assert os.path.exists(result)


@pytest.mark.asyncio
async def test_authenticode_sign_zip_nofiles(tmpdir, mocker, context):
    context.config["authenticode_cert"] = os.path.join(TEST_DATA_DIR, "windows.crt")
    context.config["authenticode_url"] = "https://example.com"
    context.config["authenticode_timestamp_style"] = None

    test_file = os.path.join(tmpdir, "partial1.mar")
    shutil.copyfile(os.path.join(TEST_DATA_DIR, "partial1.mar"), test_file)

    async def mocked_winsign(infile, outfile, *args, **kwargs):
        shutil.copyfile(infile, outfile)
        return True

    mocker.patch.object(winsign.sign, "sign_file", mocked_winsign)
    with pytest.raises(SigningScriptError):
        await sign.sign_authenticode_zip(context, test_file, "autograph_authenticode")


@pytest.mark.asyncio
async def test_authenticode_sign_zip_error(tmpdir, mocker, context):
    context.config["authenticode_cert"] = os.path.join(TEST_DATA_DIR, "windows.crt")
    context.config["authenticode_url"] = "https://example.com"
    context.config["authenticode_timestamp_style"] = None

    test_file = os.path.join(tmpdir, "windows.zip")
    shutil.copyfile(os.path.join(TEST_DATA_DIR, "windows.zip"), test_file)

    async def mocked_winsign(infile, outfile, *args, **kwargs):
        return False

    mocker.patch.object(winsign.sign, "sign_file", mocked_winsign)
    with pytest.raises(IOError):
        await sign.sign_authenticode_zip(context, test_file, "autograph_authenticode")


@pytest.mark.asyncio
async def test_authenticode_sign_authenticode_permanent_error(tmpdir, mocker, context, caplog):
    context.config["authenticode_cert"] = os.path.join(TEST_DATA_DIR, "windows.crt")
    context.config["authenticode_url"] = "https://example.com"
    context.config["authenticode_timestamp_style"] = None

    test_file = os.path.join(tmpdir, "windows.zip")
    shutil.copyfile(os.path.join(TEST_DATA_DIR, "windows.zip"), test_file)

    async def mocked_authenticode_sign(infile, outfile, *args, **kwargs):
        raise Exception("BAD!")

    async def mocked_winsign(infile, outfile, digest_algo, certs, signer, **kwargs):
        await signer("", "")
        shutil.copyfile(infile, outfile)
        return True

    mocker.patch.object(sign, "sign_hash_with_autograph", mocked_authenticode_sign)
    mocker.patch.object(winsign.sign, "sign_file", mocked_winsign)

    with pytest.raises(Exception):
        await sign.sign_authenticode_zip(context, test_file, "autograph_authenticode")

    assert "BAD!" in caplog.text


@pytest.mark.asyncio
async def test_authenticode_sign_gpg_temporary_error(tmpdir, mocker, context, caplog):
    context.task = {}
    context.task["scopes"] = ["project:releng:signing:cert:dep-signing"]
    context.autograph_configs = {
        "project:releng:signing:cert:dep-signing": [
            utils.Autograph(*["https://autograph-hsm.dev.mozaws.net", "alice", "fs5wgcer9qj819kfptdlp8gm227ewxnzvsuj9ztycsx08hfhzu", ["autograph_gpg"]])
        ]
    }
    mocked_session = MockedSession(signature="GPG SIGNATURE HERE")
    mocked_session.count = 0
    real_post = mocked_session.post

    async def flaky_post(self, *args, **kwargs):
        self.count += 1
        if self.count < 2:
            raise Exception("BAD!")
        return await real_post(*args, **kwargs)

    mocked_session.post = flaky_post.__get__(mocked_session, MockedSession)
    mocked_session.post = mock.MagicMock(wraps=mocked_session.post)

    mocker.patch.object(context, "session", new=mocked_session)

    test_file = tmpdir / "file.txt"
    test_file.write(b"hello world")

    await sign.sign_gpg_with_autograph(context, test_file, "autograph_gpg")
    hashes = []
    for call in mocked_session.post.call_args_list:
        auth = call[1]["headers"]["Authorization"]
        h = re.search(r"hash=\"(\S+)\",", auth)
        if h:
            hashes.append(h[1])
    assert len(hashes) == 2
    # Make sure that the hash of our request is always the same
    assert all(h == hashes[0] for h in hashes)


@pytest.mark.asyncio
async def test_authenticode_sign_single_file(tmpdir, mocker, context):
    context.config["authenticode_cert"] = os.path.join(TEST_DATA_DIR, "windows.crt")
    context.config["authenticode_cross_cert"] = os.path.join(TEST_DATA_DIR, "windows.crt")
    context.config["authenticode_url"] = "https://example.com"
    context.config["authenticode_timestamp_style"] = None

    await sign._extract_zipfile(context, os.path.join(TEST_DATA_DIR, "windows.zip"), tmp_dir=tmpdir)
    test_file = os.path.join(tmpdir, "helper.exe")

    async def mocked_autograph(context, from_, fmt, keyid):
        return b""

    async def mocked_winsign(infile, outfile, digest_algo, certs, signer, **kwargs):
        await signer("", "")
        shutil.copyfile(infile, outfile)
        return True

    mocker.patch.object(winsign.sign, "sign_file", mocked_winsign)
    mocker.patch.object(sign, "sign_hash_with_autograph", mocked_autograph)

    result = await sign.sign_authenticode_zip(context, test_file, "autograph_authenticode")
    assert result == test_file
    assert os.path.exists(result)


@pytest.mark.asyncio
async def test_authenticode_sign_keyids(tmpdir, mocker, context):
    context.config["authenticode_cert"] = os.path.join(TEST_DATA_DIR, "windows.crt")
    context.config["authenticode_cert_202005"] = os.path.join(TEST_DATA_DIR, "windows.crt")
    context.config["authenticode_cert_202104"] = os.path.join(TEST_DATA_DIR, "windows.crt")
    context.config["authenticode_cross_cert"] = os.path.join(TEST_DATA_DIR, "windows.crt")
    context.config["authenticode_url"] = "https://example.com"
    context.config["authenticode_timestamp_style"] = None

    await sign._extract_zipfile(context, os.path.join(TEST_DATA_DIR, "windows.zip"), tmp_dir=tmpdir)
    test_file = os.path.join(tmpdir, "helper.exe")

    async def mocked_autograph(context, from_, fmt, keyid):
        assert keyid == "202005"
        return keyid

    async def mocked_winsign(infile, outfile, digest_algo, certs, signer, **kwargs):
        await signer("", "")
        shutil.copyfile(infile, outfile)
        return True

    mocker.patch.object(winsign.sign, "sign_file", mocked_winsign)
    mocker.patch.object(sign, "sign_hash_with_autograph", mocked_autograph)

    result = await sign.sign_authenticode_zip(context, test_file, "autograph_authenticode:202005")
    assert result == test_file
    assert os.path.exists(result)

    result = await sign.sign_authenticode_zip(context, test_file, "autograph_authenticode:202104")
    assert result == test_file
    assert os.path.exists(result)
