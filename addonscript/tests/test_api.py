import contextlib
import json
import os
from contextlib import contextmanager

import aiohttp
import pytest
import pytest_asyncio
from aioresponses import aioresponses

import addonscript.api as api
from addonscript.exceptions import AMOConflictError, AuthFailedError, AuthInsufficientPermissionsError, FatalSignatureError, SignatureError


@contextmanager
def does_not_raise():
    yield


@pytest_asyncio.fixture(scope="function")
async def fake_session(event_loop):
    async with aiohttp.ClientSession() as session:
        yield session


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "statuscode,expectation",
    (
        (200, does_not_raise()),
        (201, does_not_raise()),
        (202, does_not_raise()),
        (401, pytest.raises(AuthFailedError)),
        (403, pytest.raises(AuthInsufficientPermissionsError)),
        (500, pytest.raises(aiohttp.client_exceptions.ClientResponseError)),
    ),
)
async def test_add_app_version(fake_session, context, statuscode, expectation):
    context.session = fake_session
    mocked_url = "http://some-amo-it.url/api/v4/applications/firefox/42/"

    with aioresponses() as m:
        m.put(mocked_url, status=statuscode)

        with expectation:
            await api.add_app_version(context, "42")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "statuscode,raises",
    (
        (200, None),
        (203, None),
        (302, None),
        (401, aiohttp.client_exceptions.ClientResponseError),
        (503, aiohttp.client_exceptions.ClientResponseError),
    ),
)
async def test_do_upload(fake_session, context, tmpdir, mocker, statuscode, raises):
    upload_file = "{}/test.xpi".format(tmpdir)
    context.locales = {}
    context.locales["en-GB"] = {"id": "langpack-en-GB@firefox.mozilla.org", "version": "59.0buildid20180406102847", "unsigned": upload_file}
    with open(upload_file, "wb") as f:
        f.write(b"foobar")
    expected_url = "api/v5/addons/upload/"
    mocked_url = "{}/{}".format("http://some-amo-it.url", expected_url)

    mocker.patch.object(api, "get_channel", return_value="unlisted")

    with aioresponses() as m:
        context.session = fake_session
        m.post(mocked_url, status=statuscode, body='{"foo": "bar"}')

        raisectx = contextlib.suppress()
        if raises:
            raisectx = pytest.raises(raises)
        with raisectx:
            resp = await api.do_upload(context, "en-GB")
            assert resp == {"foo": "bar"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "statuscode,retval,exception",
    (
        (200, {"id": 1234}, does_not_raise()),
        (400, None, pytest.raises(aiohttp.client_exceptions.ClientResponseError)),
        (409, None, pytest.raises(AMOConflictError)),
        (500, None, pytest.raises(aiohttp.client_exceptions.ClientResponseError)),
    ),
)
async def test_do_create_version(fake_session, context, statuscode, retval, exception):
    context.locales = {}
    context.locales["ja"] = {
        "id": "langpack-ja@firefox.mozilla.org",
        "version": "59.0buildid20180406102847",
        "name": "ja",
        "description": "japanese language pack",
    }
    context.session = fake_session
    expected_url = "api/v5/addons/addon/langpack-ja@firefox.mozilla.org/"
    data = {"version": {"id": 1234}}
    mocked_url = f"http://some-amo-it.url/{expected_url}"

    with aioresponses() as m:
        m.put(mocked_url, status=statuscode, body=json.dumps(data))
        with exception:
            assert retval == await api.do_create_version(context, "ja", "deadbeef")


@pytest.mark.asyncio
async def test_get_signed_addon_info_success(context, mocker):
    status_json = {"file": {"status": "public", "url": "https://some-download-url/foo", "size": 3, "hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}}

    async def new_version(*args, **kwargs):
        return status_json

    mocker.patch.object(api, "get_version", new=new_version)
    resp = await api.get_signed_addon_info(context, "en-GB", "deadbeef")
    assert resp == ("https://some-download-url/foo", 3, "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")


@pytest.mark.asyncio
@pytest.mark.parametrize("errors,raises", (([], False), (["deadbeef", "whimsycorn"], True), (["deadbeef"], True)))
async def test_check_upload_validation_errors(fake_session, context, errors, raises):
    expected_url = "api/v5/addons/upload/deadbeef/"
    mocked_url = "{}/{}".format("http://some-amo-it.url", expected_url)
    status_json = {"uuid": "deadbeef", "processed": True, "valid": not errors, "validation": {"errors": errors}}
    context.session = fake_session

    with aioresponses() as m:
        m.get(mocked_url, status=200, body=json.dumps(status_json))
        raisectx = contextlib.suppress()
        if raises:
            raisectx = pytest.raises(FatalSignatureError)
        with raisectx as excinfo:
            await api.check_upload(context, "deadbeef")
        if raises:
            assert "Automated validation produced" in str(excinfo.value)
            for val in errors:
                assert val in str(excinfo.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data,raises",
    (
        ({"processed": False}, pytest.raises(SignatureError)),
        ({"processed": True, "valid": True}, does_not_raise()),
    ),
)
async def test_check_upload(fake_session, context, data, raises):
    expected_url = "api/v5/addons/upload/deadbeef/"
    mocked_url = "{}/{}".format("http://some-amo-it.url", expected_url)
    context.session = fake_session

    with aioresponses() as m:
        m.get(mocked_url, status=200, body=json.dumps(data))
        with raises:
            await api.check_upload(context, "deadbeef")


@pytest.mark.asyncio
@pytest.mark.parametrize("variant,exception", (("nominated", SignatureError), ("disabled", FatalSignatureError)))
async def test_get_signed_addon_info_other_errors(context, mocker, variant, exception):
    status_json = {"file": {"status": variant}}

    async def new_version(*args, **kwargs):
        return status_json

    mocker.patch.object(api, "get_version", new=new_version)

    raisectx = pytest.raises(exception)
    with raisectx as excinfo:
        await api.get_signed_addon_info(context, "en-GB", "deadbeef")
    if variant == "nominated":
        assert "XPI not public" in str(excinfo.value)
    if variant == "disabled":
        assert 'XPI disabled on AMO' in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_signed_xpi(fake_session, context, tmpdir):
    destination = os.path.join(tmpdir, "langpack.xpi")
    download_info = ("https://addons.example.com/some/file+path", 6, "sha256:c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2")
    with aioresponses() as m:
        context.session = fake_session
        m.get(download_info[0], status=200, body=b"foobar")

        # py37 nullcontext would be better
        await api.get_signed_xpi(context, download_info, destination)
        with open(destination, "rb") as f:
            contents = f.read()
        assert contents == b"foobar"


@pytest.mark.asyncio
@pytest.mark.parametrize("contents", (b"fooba", b"foobaz"))
async def test_get_signed_xpi_error(fake_session, context, tmpdir, contents):
    destination = os.path.join(tmpdir, "langpack.xpi")
    download_info = ("https://addons.example.com/some/file+path", 6, "sha256:c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2")
    with aioresponses() as m:
        context.session = fake_session
        m.get(download_info[0], status=200, body=contents)

        with pytest.raises(SignatureError):
            await api.get_signed_xpi(context, download_info, destination)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_url,id,response,exception",
    (
        (
            "api/v5/addons/addon/langpack-en-GB@firefox.mozilla.org/versions/1234/",
            1234,
            '{"id": 1234, "version": "59.0buildid20180406102847"}',
            does_not_raise(),
        ),
        (
            "api/v5/addons/addon/langpack-en-GB@firefox.mozilla.org/versions/?filter=all_with_unlisted",
            None,
            '{"results": [{"id": 1, "version": "something else"}, {"id": 1234, "version": "59.0buildid20180406102847"}]}',
            does_not_raise(),
        ),
        (
            "api/v5/addons/addon/langpack-en-GB@firefox.mozilla.org/versions/?filter=all_with_unlisted",
            None,
            '{"results": [{"id": 1, "version": "something else"}]}',
            pytest.raises(FatalSignatureError),
        ),
    ),
)
async def test_get_version(context, fake_session, expected_url, id, response, exception):
    context.locales = {}
    context.locales["en-GB"] = {"id": "langpack-en-GB@firefox.mozilla.org", "version": "59.0buildid20180406102847"}
    mocked_url = "{}/{}".format("http://some-amo-it.url", expected_url)
    with aioresponses() as m:
        context.session = fake_session
        m.get(mocked_url, status=200, body=response)

        with exception:
            resp = await api.get_version(context, "en-GB", id)
            assert resp == {"id": 1234, "version": "59.0buildid20180406102847"}
