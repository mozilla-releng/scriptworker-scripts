import asyncio
import base64
from contextlib import contextmanager
import os
import os.path
import pytest
import shutil
import subprocess
import tarfile
import zipfile

from scriptworker_client.utils import makedirs

from iscript.exceptions import IScriptError
import iscript.autograph as autograph


# helper constants, fixtures, functions {{{1
@pytest.fixture(scope="function")
def key_config():
    return {
        "widevine_url": "https://autograph-hsm.dev.mozaws.net",
        "widevine_user": "widevine_user",
        "widevine_pass": "widevine_pass",
        "widevine_cert": "widevine_cert",
    }


async def noop_async(*args, **kwargs):
    ...


def noop_sync(*args, **kwargs):
    ...


# sign_file_with_autograph {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "to,expected,format,options",
    (
        (None, "from", "autograph_widevine", None),
        ("to", "to", "autograph_widevine", None),
    ),
)
async def test_sign_file_with_autograph(
    key_config, mocker, to, expected, format, options
):
    open_mock = mocker.mock_open(read_data=b"0xdeadbeef")
    mocker.patch("builtins.open", open_mock, create=True)

    session_mock = mocker.MagicMock()
    session_mock.post.return_value.json.return_value = [{"signed_file": "bW96aWxsYQ=="}]

    Session_mock = mocker.Mock()
    Session_mock.return_value.__enter__ = mocker.Mock(return_value=session_mock)
    Session_mock.return_value.__exit__ = mocker.Mock()
    mocker.patch("iscript.autograph.requests.Session", Session_mock, create=True)

    assert (
        await autograph.sign_file_with_autograph(key_config, "from", format, to=to)
        == expected
    )
    open_mock.assert_called()
    kwargs = {"input": "MHhkZWFkYmVlZg=="}
    if options:
        kwargs["options"] = options
    session_mock.post.assert_called_with(
        "https://autograph-hsm.dev.mozaws.net/sign/file", auth=mocker.ANY, json=[kwargs]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("to,expected", ((None, "from"), ("to", "to")))
async def test_sign_file_with_autograph_raises_http_error(
    key_config, mocker, to, expected
):
    open_mock = mocker.mock_open(read_data=b"0xdeadbeef")
    mocker.patch("builtins.open", open_mock, create=True)

    session_mock = mocker.MagicMock()
    post_mock_response = session_mock.post.return_value
    post_mock_response.raise_for_status.side_effect = (
        autograph.requests.exceptions.RequestException
    )
    post_mock_response.json.return_value = [{"signed_file": "bW96aWxsYQ=="}]

    @contextmanager
    def session_context():
        yield session_mock

    mocker.patch("iscript.autograph.requests.Session", session_context)

    async def fake_retry_async(func, args=(), attempts=5, sleeptime_kwargs=None):
        await func(*args)

    mocker.patch.object(autograph, "retry_async", new=fake_retry_async)

    with pytest.raises(autograph.requests.exceptions.RequestException):
        await autograph.sign_file_with_autograph(
            key_config, "from", "autograph_widevine", to=to
        )
    open_mock.assert_called()


# sign_widevine_dir {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename,fmt,should_sign,orig_files",
    (
        ("foo.tar.gz", "widevine", True, None),
        ("foo.zip", "widevine_blessed", True, None),
        (
            "foo.dmg",
            "widevine",
            True,
            [
                "foo.app/Contents/MacOS/firefox",
                "foo.app/Contents/MacOS/bar.app/Contents/MacOS/plugin-container",
                "foo.app/ignore",
            ],
        ),
        ("foo.zip", "widevine", False, None),
        ("foo.dmg", "widevine", False, None),
        ("foo.tar.bz2", "widevine", False, None),
        ("foo.zip", "autograph_widevine", True, None),
        ("foo.dmg", "autograph_widevine", True, None),
        ("foo.tar.bz2", "autograph_widevine", True, None),
    ),
)
async def test_sign_widevine_dir(
    key_config, mocker, filename, fmt, should_sign, orig_files, tmp_path
):
    if should_sign:
        files = orig_files or [
            "isdir/firefox",
            "firefox/firefox",
            "y/plugin-container",
            "z/blah",
            "ignore",
        ]
    else:
        files = orig_files or ["z/blah", "ignore"]

    def fake_walk(_):
        yield ("", [], files)

    config = {"artifact_dir": tmp_path / "artifacts"}

    async def fake_filelist(*args, **kwargs):
        return files

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

    mocker.patch.object(autograph, "sign_widevine_with_autograph", new=noop_async)
    mocker.patch.object(autograph, "makedirs", new=noop_sync)
    mocker.patch.object(autograph, "generate_precomplete", new=noop_sync)
    mocker.patch.object(autograph, "_run_generate_precomplete", new=noop_sync)
    mocker.patch.object(os.path, "isfile", new=fake_isfile)
    mocker.patch.object(os, "walk", new=fake_walk)

    await autograph.sign_widevine_dir(config, key_config, filename)


# _get_widevine_signing_files {{{1
@pytest.mark.parametrize(
    "filenames,expected",
    (
        (["firefox.dll", "XUL.so", "firefox.bin", "blah"], {}),
        (
            (
                "firefox",
                "blah/XUL",
                "foo/bar/libclearkey.dylib",
                "baz/plugin-container",
                "ignore",
            ),
            {
                "firefox": "widevine",
                "blah/XUL": "widevine",
                "foo/bar/libclearkey.dylib": "widevine",
                "baz/plugin-container": "widevine_blessed",
            },
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
    assert autograph._get_widevine_signing_files(filenames) == expected


# _run_generate_precomplete {{{1
@pytest.mark.parametrize("num_precomplete,raises", ((1, False), (0, True), (2, True)))
def test_run_generate_precomplete(tmp_path, num_precomplete, raises, mocker):
    mocker.patch.object(autograph, "generate_precomplete", new=noop_sync)
    work_dir = tmp_path / "work"
    config = {"artifact_dir": tmp_path / "artifacts"}
    for i in range(0, num_precomplete):
        path = os.path.join(work_dir, "foo", str(i))
        makedirs(path)
        with open(os.path.join(path, "precomplete"), "w") as fh:
            fh.write("blah")
    if raises:
        with pytest.raises(IScriptError):
            autograph._run_generate_precomplete(config, work_dir)
    else:
        autograph._run_generate_precomplete(config, work_dir)


# remove_extra_files {{{1
def test_remove_extra_files(tmp_path):
    extra = ["a", "b/c"]
    good = ["d", "e/f"]
    work_dir = tmp_path
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
    output = autograph.remove_extra_files(work_dir, all_files)
    for f in extra:
        path = os.path.realpath(os.path.join(work_dir, f))
        assert path in output
        assert not os.path.exists(path)
    for f in good:
        assert os.path.exists(os.path.join(work_dir, f))


# autograph {{{1
@pytest.mark.parametrize(
    "input_bytes, fmt, keyid, expected",
    (
        (b"asdf", "widevine", None, [{"input": "YXNkZg=="}]),
        (
            b"asdf",
            "autograph_widevine",
            "key1",
            [{"input": "YXNkZg==", "keyid": "key1"}],
        ),
    ),
)
def test_make_signing_req(input_bytes, fmt, keyid, expected):
    assert autograph.make_signing_req(input_bytes, fmt, keyid=keyid) == expected


@pytest.mark.asyncio
async def test_bad_autograph_method():
    with pytest.raises(IScriptError):
        await autograph.sign_with_autograph(None, None, None, "badformat")


@pytest.mark.asyncio
@pytest.mark.parametrize("blessed", (True, False))
async def test_widevine_autograph(mocker, tmp_path, blessed, key_config):
    wv = mocker.patch("iscript.autograph.widevine")
    wv.generate_widevine_hash.return_value = b"hashhashash"
    wv.generate_widevine_signature.return_value = b"sigwidevinesig"

    async def fake_call(*args, **kwargs):
        return [{"signature": base64.b64encode(b"sigwidevinesig")}]

    mocker.patch.object(autograph, "call_autograph", fake_call)

    cert = tmp_path / "widevine.crt"
    cert.write_bytes(b"TMPCERT")
    key_config["widevine_cert"] = cert

    to = tmp_path / "signed.sig"
    to = await autograph.sign_widevine_with_autograph(
        key_config, "from", blessed, to=to
    )

    assert b"sigwidevinesig" == to.read_bytes()


@pytest.mark.asyncio
async def test_no_widevine(mocker, tmp_path):
    async def fake_call(*args, **kwargs):
        return [{"signature": b"sigautographsig"}]

    mocker.patch.object(autograph, "call_autograph", fake_call)

    with pytest.raises(ImportError):
        to = tmp_path / "signed.sig"
        to = await autograph.sign_widevine_with_autograph({}, "from", True, to=to)
