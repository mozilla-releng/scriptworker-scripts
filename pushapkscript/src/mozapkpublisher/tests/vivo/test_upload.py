import hashlib

import pytest

from .common import PUBLIC_PARAM_NAMES, ROUTER_URL, basic_headers, business_failure, posted_upload_fields, recorded_calls, success
from .fixtures import ACCESS_KEY, ACCESS_SECRET
from mozapkpublisher.vivo_api import METHOD_UPLOAD_APK, VivoAppStoreApi
from mozapkpublisher.vivo_api.auth import sign_params
from mozapkpublisher.vivo_api.error import VivoException, VivoUploadException

PACKAGE_NAME = "org.mozilla.firefox"


def _md5(path):
    with open(path, "rb") as fh:
        return hashlib.md5(fh.read()).hexdigest()


def _upload_payload(apk_path, **overrides):
    data = {
        "packageName": PACKAGE_NAME,
        "fileMd5": _md5(apk_path),
        "serialNumber": "serial-123",
        "versionCode": 100,
        "versionName": "1.0.0",
    }
    data.update(overrides)
    return success(data)


@pytest.mark.asyncio
async def test_upload_apk_returns_the_data_object(vivo, responses_mock, apk_path):
    responses_mock.post(ROUTER_URL, payload=_upload_payload(apk_path))

    result = await vivo.upload_apk(PACKAGE_NAME, apk_path, "firefox-arm64-v8a-116.0.apk")

    assert result["serialNumber"] == "serial-123"
    assert result["versionCode"] == 100
    assert result["versionName"] == "1.0.0"


@pytest.mark.asyncio
async def test_upload_apk_sends_the_file_and_its_md5(vivo, responses_mock, apk_path):
    """The binary rides as the `file` part under the name the store should record, and
    `fileMd5` is the digest of what is actually being sent -- vivo rejects a mismatch
    with subCode A0114."""
    responses_mock.post(ROUTER_URL, payload=_upload_payload(apk_path))

    await vivo.upload_apk(PACKAGE_NAME, apk_path, "firefox-arm64-v8a-116.0.apk")

    fields = posted_upload_fields(responses_mock)
    assert fields["file"][0] == "firefox-arm64-v8a-116.0.apk"
    assert fields["fileMd5"][1] == _md5(apk_path)
    assert fields["packageName"][1] == PACKAGE_NAME
    assert fields["method"][1] == METHOD_UPLOAD_APK


@pytest.mark.asyncio
async def test_upload_apk_signs_every_field_except_the_file(vivo, responses_mock, apk_path):
    """The whole parameter set travels in the multipart body and is signed there. The
    file itself is excluded from the signature: its bytes are not a signable value."""
    responses_mock.post(ROUTER_URL, payload=_upload_payload(apk_path))

    await vivo.upload_apk(PACKAGE_NAME, apk_path, "firefox.apk")

    fields = posted_upload_fields(responses_mock)
    assert PUBLIC_PARAM_NAMES.issubset(fields.keys())

    signed = {name: value for name, (_filename, value) in fields.items() if name not in ("sign", "file")}
    assert fields["sign"][1] == sign_params(signed, ACCESS_SECRET)


@pytest.mark.asyncio
async def test_upload_apk_sends_no_authorization_header(vivo, responses_mock, apk_path):
    """vivo authenticates the signed `sign` parameter in the body, so there is no
    Authorization header to send."""
    responses_mock.post(ROUTER_URL, payload=_upload_payload(apk_path))

    await vivo.upload_apk(PACKAGE_NAME, apk_path, "firefox.apk")

    assert recorded_calls(responses_mock)[0].kwargs["headers"] == basic_headers()


@pytest.mark.asyncio
async def test_upload_apk_rejects_a_mismatched_md5(vivo, responses_mock, apk_path):
    """vivo echoes back the MD5 it computed over what it received, so unlike the other
    stores a corrupted upload can be caught by checksum rather than by size."""
    responses_mock.post(ROUTER_URL, payload=_upload_payload(apk_path, fileMd5="0" * 32))

    with pytest.raises(VivoUploadException, match="different than what was uploaded"):
        await vivo.upload_apk(PACKAGE_NAME, apk_path, "firefox.apk")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    (
        pytest.param(success({"packageName": PACKAGE_NAME}), id="no_serial_number"),
        pytest.param(success({"serialNumber": ""}), id="empty_serial_number"),
        pytest.param(success(None), id="null_data"),
        pytest.param(success({}), id="empty_data"),
    ),
)
async def test_upload_apk_without_a_serial_number_is_an_error(vivo, responses_mock, apk_path, payload):
    """The serial number identifies the uploaded binary. A response missing it means the
    upload did not land, however cheerful the envelope looks."""
    responses_mock.post(ROUTER_URL, payload=payload)

    with pytest.raises(VivoUploadException, match="didn't contain a serial number"):
        await vivo.upload_apk(PACKAGE_NAME, apk_path, "firefox.apk")


@pytest.mark.asyncio
async def test_upload_apk_surfaces_a_business_failure(vivo, responses_mock, apk_path):
    responses_mock.post(ROUTER_URL, payload=business_failure("A0113", "The uploaded APK package name is not consistent"))

    with pytest.raises(VivoException, match="not consistent"):
        await vivo.upload_apk(PACKAGE_NAME, apk_path, "firefox.apk")


@pytest.mark.asyncio
async def test_upload_apk_closes_the_file(responses_mock, apk_path):
    async with VivoAppStoreApi("k", "s") as vivo:
        responses_mock.post(ROUTER_URL, payload=_upload_payload(apk_path))
        await vivo.upload_apk(PACKAGE_NAME, apk_path, "firefox.apk")

    fields = posted_upload_fields(responses_mock)
    assert fields["file"][1].closed


@pytest.mark.asyncio
async def test_the_client_has_no_wall_clock_deadline(vivo):
    """aiohttp's default `total=300` covers the body write and would kill a large upload
    that is progressing fine. A stalled connection still has to fail, hence the
    socket-level guards."""
    timeout = vivo._client.timeout

    assert timeout.total is None
    assert timeout.sock_connect == 30
    assert timeout.sock_read == 600


@pytest.mark.asyncio
async def test_the_request_log_names_the_resolved_url_and_the_interface(vivo, responses_mock, caplog):
    """Every interface posts to the same route, so the URL alone does not identify the
    call. Logging the resolved URL is what makes a repointed BASE_URL/ROUTER_ROUTE
    visible while testing against a scratch server."""
    responses_mock.post(ROUTER_URL, payload=success({"serialNumber": "s"}))

    with caplog.at_level("INFO"):
        await vivo.get_app_detail(PACKAGE_NAME)

    assert "POST {} (method=app.detail)".format(ROUTER_URL) in caplog.text


@pytest.mark.asyncio
async def test_the_request_log_leaks_no_credentials(vivo, responses_mock, caplog, apk_path):
    """The signed parameters carry the access key and a signature derived from the access
    secret. Logging the request must not turn an operator's terminal or a task log into a
    place credentials end up."""
    responses_mock.post(ROUTER_URL, payload=_upload_payload(apk_path))

    with caplog.at_level("INFO"):
        await vivo.upload_apk(PACKAGE_NAME, apk_path, "firefox.apk")

    sent = posted_upload_fields(responses_mock)
    assert ACCESS_SECRET not in caplog.text
    assert ACCESS_KEY not in caplog.text
    assert sent["sign"][1] not in caplog.text
