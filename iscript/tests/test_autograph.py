import base64
import os
import os.path
import shutil
from contextlib import contextmanager
from hashlib import sha256

import pytest
from scriptworker_client.utils import makedirs

import iscript.autograph as autograph
from iscript.exceptions import IScriptError
from iscript.mac import App

# helper constants, fixtures, functions {{{1
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


@contextmanager
def does_not_raise():
    yield


@pytest.fixture(scope="function")
def sign_config():
    return {
        "widevine_url": "https://autograph-hsm.dev.mozaws.net",
        "widevine_user": "widevine_user",
        "widevine_pass": "widevine_pass",
        "widevine_cert": "widevine_cert",
        "langpack_url": "https://autograph-hsm.dev.mozaws.net/langpack",
        "langpack_user": "langpack_user",
        "langpack_pass": "langpack_pass",
        "omnija_url": "https://autograph-hsm.dev.mozaws.net/omnija",
        "omnija_user": "omnija_user",
        "omnija_pass": "omnija_pass",
        "stage_widevine_url": "https://autograph-stage.dev.mozaws.net",
        "stage_widevine_user": "widevine_user",
        "stage_widevine_pass": "widevine_pass",
        "stage_widevine_cert": "widevine_cert",
        "stage_langpack_url": "https://autograph-stage.dev.mozaws.net/langpack",
        "stage_langpack_user": "langpack_user",
        "stage_langpack_pass": "langpack_pass",
        "stage_omnija_url": "https://autograph-stage.dev.mozaws.net/omnija",
        "stage_omnija_user": "omnija_user",
        "stage_omnija_pass": "omnija_pass",
        "gcp_prod_widevine_url": "https://autograph-gcp.dev.mozaws.net",
        "gcp_prod_widevine_user": "widevine_user",
        "gcp_prod_widevine_pass": "widevine_pass",
        "gcp_prod_widevine_cert": "widevine_cert",
        "gcp_prod_langpack_url": "https://autograph-gcp.dev.mozaws.net/langpack",
        "gcp_prod_langpack_user": "langpack_user",
        "gcp_prod_langpack_pass": "langpack_pass",
        "gcp_prod_omnija_url": "https://autograph-gcp.dev.mozaws.net/omnija",
        "gcp_prod_omnija_user": "omnija_user",
        "gcp_prod_omnija_pass": "omnija_pass",
    }


async def noop_async(*args, **kwargs): ...


def noop_sync(*args, **kwargs): ...


# sign_file_with_autograph {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "to,expected,format,url",
    (
        (None, "from", "autograph_widevine", "https://autograph-hsm.dev.mozaws.net"),
        ("to", "to", "autograph_widevine", "https://autograph-hsm.dev.mozaws.net"),
        ("to", "to", "stage_autograph_widevine", "https://autograph-stage.dev.mozaws.net"),
        ("to", "to", "gcp_prod_autograph_widevine", "https://autograph-gcp.dev.mozaws.net"),
    ),
)
async def test_sign_file_with_autograph(sign_config, mocker, to, expected, format, url):
    open_mock = mocker.mock_open(read_data=b"0xdeadbeef")
    mocker.patch("builtins.open", open_mock, create=True)

    session_mock = mocker.MagicMock()
    session_mock.post.return_value.json.return_value = [{"signed_file": "bW96aWxsYQ=="}]

    Session_mock = mocker.Mock()
    Session_mock.return_value.__enter__ = mocker.Mock(return_value=session_mock)
    Session_mock.return_value.__exit__ = mocker.Mock()
    mocker.patch("iscript.autograph.requests.Session", Session_mock, create=True)

    assert await autograph.sign_file_with_autograph(sign_config, "from", format, to=to) == expected
    open_mock.assert_called()
    kwargs = {"input": "MHhkZWFkYmVlZg=="}
    expected_url = f"{url}/sign/file"
    session_mock.post.assert_called_with(expected_url, auth=mocker.ANY, json=[kwargs])


@pytest.mark.asyncio
@pytest.mark.parametrize("to,expected", ((None, "from"), ("to", "to")))
async def test_sign_file_with_autograph_raises_http_error(sign_config, mocker, to, expected):
    open_mock = mocker.mock_open(read_data=b"0xdeadbeef")
    mocker.patch("builtins.open", open_mock, create=True)

    session_mock = mocker.MagicMock()
    post_mock_response = session_mock.post.return_value
    post_mock_response.raise_for_status.side_effect = autograph.requests.exceptions.RequestException
    post_mock_response.json.return_value = [{"signed_file": "bW96aWxsYQ=="}]

    @contextmanager
    def session_context():
        yield session_mock

    mocker.patch("iscript.autograph.requests.Session", session_context)

    async def fake_retry_async(func, args=(), attempts=5, sleeptime_kwargs=None):
        await func(*args)

    mocker.patch.object(autograph, "retry_async", new=fake_retry_async)

    with pytest.raises(autograph.requests.exceptions.RequestException):
        await autograph.sign_file_with_autograph(sign_config, "from", "autograph_widevine", to=to)
    open_mock.assert_called()


# sign_widevine_dir {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename,fmt,should_sign,orig_files",
    (
        ("foo.tar.gz", "widevine", True, None),
        ("foo.zip", "widevine_blessed", True, None),
        ("foo.dmg", "widevine", True, ["foo.app/Contents/MacOS/firefox", "foo.app/Contents/MacOS/bar.app/Contents/MacOS/plugin-container", "foo.app/ignore"]),
        ("foo.zip", "widevine", False, None),
        ("foo.dmg", "widevine", False, None),
        ("foo.tar.bz2", "widevine", False, None),
        ("foo.zip", "autograph_widevine", True, None),
        ("foo.dmg", "autograph_widevine", True, None),
        ("foo.tar.bz2", "autograph_widevine", True, None),
    ),
)
async def test_sign_widevine_dir(sign_config, mocker, filename, fmt, should_sign, orig_files, tmp_path):
    if should_sign:
        files = orig_files or ["isdir/firefox", "firefox/firefox", "y/plugin-container", "z/blah", "ignore"]
    else:
        files = orig_files or ["z/blah", "ignore"]

    def fake_walk(_):
        yield ("", [], files)

    config = {"artifact_dir": tmp_path / "artifacts"}

    def fake_isfile(path):
        return "isdir" not in path

    mocker.patch.object(autograph, "sign_widevine_with_autograph", new=noop_async)
    mocker.patch.object(autograph, "makedirs", new=noop_sync)
    mocker.patch.object(autograph, "generate_precomplete", new=noop_sync)
    mocker.patch.object(autograph, "_run_generate_precomplete", new=noop_sync)
    mocker.patch.object(os.path, "isfile", new=fake_isfile)
    mocker.patch.object(os, "walk", new=fake_walk)

    await autograph.sign_widevine_dir(config, sign_config, filename, fmt)


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
    "input_bytes, fmt, extension_id, keyid, expected",
    (
        (b"asdf", "widevine", None, None, [{"input": "YXNkZg=="}]),
        (b"asdf", "autograph_widevine", None, "key1", [{"input": "YXNkZg==", "keyid": "key1"}]),
        (
            b"asdf",
            "autograph_omnija",
            "omni.ja@mozilla.org",
            None,
            [{"input": "YXNkZg==", "options": {"id": "omni.ja@mozilla.org", "cose_algorithms": ["ES256"], "pkcs7_digest": "SHA256"}}],
        ),
    ),
)
def test_make_signing_req(input_bytes, fmt, extension_id, keyid, expected):
    assert autograph.make_signing_req(input_bytes, fmt, keyid=keyid, extension_id=extension_id) == expected


@pytest.mark.asyncio
async def test_bad_autograph_method():
    with pytest.raises(IScriptError):
        await autograph.sign_with_autograph(None, None, None, "badformat")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "blessed,fmt,expected_url",
    (
        (True, "autograph_widevine", "https://autograph-hsm.dev.mozaws.net"),
        (False, "autograph_widevine", "https://autograph-hsm.dev.mozaws.net"),
        (False, "stage_autograph_widevine", "https://autograph-stage.dev.mozaws.net"),
        (False, "gcp_prod_autograph_widevine", "https://autograph-gcp.dev.mozaws.net"),
    ),
)
async def test_widevine_autograph(mocker, tmp_path, blessed, sign_config, fmt, expected_url):
    wv = mocker.patch("iscript.autograph.widevine")
    wv.generate_widevine_hash.return_value = b"hashhashash"
    wv.generate_widevine_signature.return_value = b"sigwidevinesig"

    async def fake_call(url, *args, **kwargs):
        assert expected_url in url
        return [{"signature": base64.b64encode(b"sigwidevinesig")}]

    mocker.patch.object(autograph, "call_autograph", fake_call)

    cert = tmp_path / "widevine.crt"
    cert.write_bytes(b"TMPCERT")
    sign_config["widevine_cert"] = cert

    to = tmp_path / "signed.sig"
    to = await autograph.sign_widevine_with_autograph(sign_config, "from", fmt, blessed, to=to)

    assert b"sigwidevinesig" == to.read_bytes()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fmt,expected_url",
    (
        ("autograph_omnija", "https://autograph-hsm.dev.mozaws.net"),
        ("autograph_omnija", "https://autograph-hsm.dev.mozaws.net"),
        ("stage_autograph_omnija", "https://autograph-stage.dev.mozaws.net"),
        ("gcp_prod_autograph_omnija", "https://autograph-gcp.dev.mozaws.net"),
    ),
)
async def test_omnija_autograph(mocker, tmp_path, sign_config, fmt, expected_url):
    orig = tmp_path / "omni.ja"
    with open(orig, "w+") as f:
        f.write("")

    merge = mocker.patch("iscript.autograph.merge_omnija_files")
    merge.side_effect = lambda orig, signed, to: shutil.copy(signed, to)

    async def fake_call(url, *args, **kwargs):
        assert expected_url in url
        return [{"signed_file": base64.b64encode(b"sigomnijasig")}]

    mocker.patch.object(autograph, "call_autograph", fake_call)

    config = {"work_dir": tmp_path}
    await autograph.sign_omnija_with_autograph(config, sign_config, tmp_path, fmt)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fmt,expected_url",
    (
        ("autograph_langpack", "https://autograph-hsm.dev.mozaws.net"),
        ("stage_autograph_langpack", "https://autograph-stage.dev.mozaws.net"),
        ("gcp_prod_autograph_langpack", "https://autograph-gcp.dev.mozaws.net"),
    ),
)
async def test_langpack_autograph(mocker, tmp_path, sign_config, fmt, expected_url):
    dir = tmp_path / "public" / "build"
    os.makedirs(dir)
    orig = dir / "test.xpi"
    with open(orig, "w+") as f:
        f.write("")

    lid = mocker.patch("iscript.autograph.langpack_id")
    lid.return_value = "test-xpi"

    async def fake_call(url, *args, **kwargs):
        assert expected_url in url
        return [{"signed_file": base64.b64encode(b"siglangpacksig")}]

    mocker.patch.object(autograph, "call_autograph", fake_call)

    config = {"artifact_dir": tmp_path}
    app = App()
    app.orig_path = orig.as_posix()
    app.artifact_prefix = "public/build"
    await autograph.sign_langpacks(config, sign_config, [app], fmt)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fmt,expected_url",
    (
        ("autograph_widevine", "https://autograph-hsm.dev.mozaws.net"),
        ("stage_autograph_widevine", "https://autograph-stage.dev.mozaws.net"),
        ("gcp_prod_autograph_widevine", "https://autograph-gcp.dev.mozaws.net"),
    ),
)
async def test_no_widevine(mocker, tmp_path, fmt, expected_url):
    async def fake_call(url, *args, **kwargs):
        assert expected_url in url
        return [{"signature": b"sigautographsig"}]

    mocker.patch.object(autograph, "call_autograph", fake_call)

    with pytest.raises(ImportError):
        to = tmp_path / "signed.sig"
        to = await autograph.sign_widevine_with_autograph({}, "from", fmt, True, to=to)


# omnija {{{1
@pytest.mark.parametrize(
    "filenames,expected",
    (
        (["firefox.dll", "XUL.so", "firefox.bin", "blah"], {}),
        (
            ("firefox", "blah/omni.ja", "foo/bar/libclearkey.dylib", "baz/omni.ja", "ignore"),
            {"blah/omni.ja": "autograph_omnija", "baz/omni.ja": "autograph_omnija"},
        ),
    ),
)
def test_get_omnija_signing_files(filenames, expected):
    assert autograph._get_omnija_signing_files(filenames) == expected


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

    mocker.patch.object(autograph.zipfile, "ZipFile", mockedZipFile)
    await autograph.merge_omnija_files(copy_from, "signed.ja", copy_to)
    assert open(copy_from, "rb").read() == open(copy_to, "rb").read()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "orig,signed,sha256_expected",
    (
        ("no_preload_unsigned_omni.ja", "no_preload_signed_omni.ja", "9b05478ca8774d13c9a5f1699b90a10ffd283b9a21b8ebe4653cd63f052cf107"),
        ("preload_unsigned_omni.ja", "preload_signed_omni.ja", "c353145c32cb3b251d65f85bcdba0c96d361292dad932b85d30f1dfe0b073e3f"),
    ),
)
async def test_omnija_sign(tmpdir, mocker, orig, signed, sha256_expected):
    copy_from = os.path.join(tmpdir, "omni.ja")
    shutil.copyfile(os.path.join(TEST_DATA_DIR, orig), copy_from)
    config = {"work_dir": tmpdir}
    sign_config = {}

    async def mocked_autograph(sign_config, from_, fmt, to, keyid, extension_id):
        assert fmt == "autograph_omnija"
        assert extension_id == "omni.ja@mozilla.org"
        assert keyid
        shutil.copyfile(os.path.join(TEST_DATA_DIR, signed), to)

    mocker.patch.object(autograph, "sign_file_with_autograph", mocked_autograph)
    await autograph.sign_omnija_with_autograph(config, sign_config, tmpdir, "autograph_omnija")
    sha256_actual = sha256(open(copy_from, "rb").read()).hexdigest()
    assert sha256_actual == sha256_expected


def test_langpack_id_regex():
    assert autograph.LANGPACK_RE.match("langpack-en-CA@firefox.mozilla.org") is not None
    assert autograph.LANGPACK_RE.match("langpack-ja-JP-mac@devedition.mozilla.org") is not None
    assert autograph.LANGPACK_RE.match("invalid-langpack-id@example.com") is None


def test_langpack_id():
    filename = os.path.join(TEST_DATA_DIR, "en-CA.xpi")
    langpack_app = App(orig_path=filename, formats=["autograph_langpack"], artifact_prefix="public/")
    assert autograph.langpack_id(langpack_app) == "langpack-en-CA@firefox.mozilla.org"


def test_langpack_id():
    filename = os.path.join(TEST_DATA_DIR, "en-CA.exe")
    langpack_app = App(orig_path=filename, formats=["autograph_langpack"], artifact_prefix="public/")
    with pytest.raises(IScriptError):
        assert autograph.langpack_id(langpack_app) == "langpack-en-CA@firefox.mozilla.org"


@pytest.mark.parametrize(
    "json_,raises",
    (
        ({}, pytest.raises(IScriptError)),
        ({"languages": {}}, pytest.raises(IScriptError)),
        ({"languages": {}, "langpack_id": "en-CA"}, pytest.raises(IScriptError)),
        ({"languages": {}, "langpack_id": "en-CA", "applications": {}}, pytest.raises(IScriptError)),
        ({"languages": {}, "langpack_id": "en-CA", "applications": {"gecko": {}}}, pytest.raises(IScriptError)),
        ({"languages": {}, "langpack_id": "en-CA", "applications": {"gecko": {}}}, pytest.raises(IScriptError)),
        ({"languages": {}, "langpack_id": "en-CA", "applications": {"gecko": {"id": ""}}}, pytest.raises(IScriptError)),
        ({"languages": {}, "langpack_id": "en-CA", "applications": {"gecko": {"id": "invalid-langpack-id@example.com"}}}, pytest.raises(IScriptError)),
        ({"languages": {}, "langpack_id": "en-CA", "applications": {"gecko": {"id": "langpack-en-CA@firefox.mozilla.org"}}}, does_not_raise()),
        ({"languages": {}, "langpack_id": "en-CA", "applications": {"gecko": {"id": "langpack-de@devedition.mozilla.org"}}}, does_not_raise()),
        ({"languages": {}, "langpack_id": "en-CA", "applications": {"gecko": {"id": "langpack-ja-JP-mac@devedition.mozilla.org"}}}, does_not_raise()),
        ({"langpack_id": "en-CA", "applications": {"gecko": {"id": "langpack-en-CA@firefox.mozilla.org"}}}, pytest.raises(IScriptError)),
        ({"languages": {}, "langpack_id": "en-CA", "browser_specific_settings": {}}, pytest.raises(IScriptError)),
        ({"languages": {}, "langpack_id": "en-CA", "browser_specific_settings": {"gecko": {}}}, pytest.raises(IScriptError)),
        ({"languages": {}, "langpack_id": "en-CA", "browser_specific_settings": {"gecko": {}}}, pytest.raises(IScriptError)),
        ({"languages": {}, "langpack_id": "en-CA", "browser_specific_settings": {"gecko": {"id": ""}}}, pytest.raises(IScriptError)),
        (
            {"languages": {}, "langpack_id": "en-CA", "browser_specific_settings": {"gecko": {"id": "invalid-langpack-id@example.com"}}},
            pytest.raises(IScriptError),
        ),
        ({"languages": {}, "langpack_id": "en-CA", "browser_specific_settings": {"gecko": {"id": "langpack-en-CA@firefox.mozilla.org"}}}, does_not_raise()),
        ({"languages": {}, "langpack_id": "en-CA", "browser_specific_settings": {"gecko": {"id": "langpack-de@devedition.mozilla.org"}}}, does_not_raise()),
        (
            {"languages": {}, "langpack_id": "en-CA", "browser_specific_settings": {"gecko": {"id": "langpack-ja-JP-mac@devedition.mozilla.org"}}},
            does_not_raise(),
        ),
        ({"langpack_id": "en-CA", "browser_specific_settings": {"gecko": {"id": "langpack-en-CA@firefox.mozilla.org"}}}, pytest.raises(IScriptError)),
    ),
)
def test_langpack_id_raises(json_, raises, mocker):
    filename = os.path.join(TEST_DATA_DIR, "en-CA.xpi")
    langpack_app = App(orig_path=filename, formats=["autograph_langpck"], artifact_prefix="public/")

    def load_manifest(*args, **kwargs):
        return json_

    # Mock ZipFile so we don't actually read the xpi data
    mocker.patch.object(autograph.zipfile, "ZipFile", autospec=True)

    mocker.patch.object(autograph.json, "load", load_manifest)
    with raises:
        id = autograph.langpack_id(langpack_app)
        browser_specific_settings = json_.get("browser_specific_settings", json_.get("applications", {}))
        assert id == browser_specific_settings["gecko"]["id"]


@pytest.mark.asyncio
async def test_langpack_sign(sign_config, mocker, tmp_path):
    mock_ever_called = [False]
    filename = os.path.join(TEST_DATA_DIR, "en-CA.xpi")
    langpack_app = App(orig_path=filename, formats=["autograph_langpack"], artifact_prefix=TEST_DATA_DIR)
    config = {"artifact_dir": tmp_path / "artifacts"}

    async def mocked_call_autograph(url, user, password, request_json):
        mock_ever_called[0] = True
        # url/user/pass comes from test sign_config
        assert url.startswith("https://autograph-hsm.dev.mozaws.net/langpack")
        assert user == "langpack_user"
        assert password == "langpack_pass"
        assert len(request_json) == 1
        assert request_json[0]["options"]["id"] == "langpack-en-CA@firefox.mozilla.org"
        return [{"signed_file": base64.b64encode(open(filename, "rb").read())}]

    mock_obj = mocker.patch.object(autograph, "call_autograph", new=mocked_call_autograph)

    await autograph.sign_langpacks(config, sign_config, [langpack_app], "autograph_langpack")
    expected_hash = "7f4292927b4a26589ee912918de941f498e58ce100041ec3565a82da57a42eab"
    assert sha256(open(langpack_app.target_bundle_path, "rb").read()).hexdigest() == expected_hash
    assert mock_ever_called[0]
