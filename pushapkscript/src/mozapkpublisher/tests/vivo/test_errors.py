import aiohttp
import pytest

from .common import ROUTER_URL, business_failure, success
from mozapkpublisher.vivo_api.error import (
    VivoAuthenticationException,
    VivoAuthorizationException,
    VivoException,
    VivoUpdateException,
)
from mozapkpublisher.vivo_api.utils import RESULT_CODES_DOC_URL, raise_for_response_code, response_data, unwrap_nested_envelope


@pytest.mark.parametrize(
    "body",
    (
        pytest.param(success(), id="both_levels_zero"),
        pytest.param({"code": "0", "subCode": None, "msg": "success"}, id="null_sub_code"),
        pytest.param({"code": "0"}, id="no_sub_code"),
        pytest.param({"data": {"serialNumber": "1"}}, id="no_envelope"),
        pytest.param({"code": 0, "subCode": 0}, id="numeric_zeroes"),
    ),
)
def test_raise_for_response_code_accepts(body):
    assert raise_for_response_code(body) is None


def test_raise_for_response_code_rejects_a_gateway_failure():
    """A gateway failure carries no `subCode` at all, so the outer `code` has to be
    enough on its own."""
    with pytest.raises(VivoException) as exc:
        raise_for_response_code({"code": "23", "msg": "Signature illegal, please check again", "success": False})

    message = str(exc.value)
    assert "23" in message
    assert "Signature illegal" in message
    assert RESULT_CODES_DOC_URL in message


def test_raise_for_response_code_rejects_a_business_failure_claiming_success():
    """The trap this function exists for: vivo reports a refused publication as HTTP 200
    with `"code": "0"`, `"msg": "success"` and `"success": true`. Believing any of those
    would read a failure as a completed release."""
    with pytest.raises(VivoException) as exc:
        raise_for_response_code(business_failure("A0301", "The app does not exist"))

    message = str(exc.value)
    assert "A0301" in message
    assert "The app does not exist" in message


@pytest.mark.parametrize(
    "sub_code,expected_reason",
    (
        pytest.param("A0305", "already under review", id="A0305"),
        pytest.param("A0306", "pending publication", id="A0306"),
        pytest.param("A0307", "being tested", id="A0307"),
        pytest.param("B0302", "already being updated", id="B0302"),
    ),
)
def test_app_state_subcodes_explain_themselves(sub_code, expected_reason):
    """These four mean a human has to act in the vivo console. The error says which state
    the app is in, rather than leaving an operator to look the code up."""
    with pytest.raises(VivoUpdateException) as exc:
        raise_for_response_code(business_failure(sub_code, "some vivo prose"))

    message = str(exc.value)
    assert expected_reason in message
    assert sub_code in message
    assert "vivo Developers console" in message


def test_gateway_failure_takes_precedence_over_a_business_code():
    """When the gateway rejects a request there is no business result to report, so the
    gateway's own code is what gets raised."""
    with pytest.raises(VivoException, match="code=23"):
        raise_for_response_code({"code": "23", "msg": "Signature illegal", "subCode": "A0305"})


@pytest.mark.asyncio
async def test_in_band_error_on_an_http_200_is_raised(vivo, responses_mock):
    responses_mock.post(ROUTER_URL, status=200, payload=business_failure("A0301", "The app does not exist"))

    with pytest.raises(VivoException, match="The app does not exist"):
        await vivo.get_app_detail("org.mozilla.firefox")


@pytest.mark.asyncio
async def test_401_raises_an_authentication_error(vivo, responses_mock):
    responses_mock.post(ROUTER_URL, status=401, payload={"code": "23", "msg": "Signature illegal, please check again", "success": False})

    with pytest.raises(VivoAuthenticationException, match="Signature illegal"):
        await vivo.get_app_detail("org.mozilla.firefox")


@pytest.mark.asyncio
async def test_403_raises_an_authorization_error(vivo, responses_mock):
    """A 403 means the access key lacks the publishing permission. Reporting it as an
    authentication failure would send operators off rotating a healthy key."""
    responses_mock.post(ROUTER_URL, status=403, payload={"code": "1", "msg": "Insufficient permission", "success": False})

    with pytest.raises(VivoAuthorizationException, match="Insufficient permission"):
        await vivo.get_app_detail("org.mozilla.firefox")


@pytest.mark.asyncio
async def test_error_body_prefers_sub_msg(vivo, responses_mock):
    """On a business failure `msg` is the useless string "success", so the message that
    reaches the operator has to come from `subMsg`."""
    responses_mock.post(ROUTER_URL, status=500, payload={"code": "0", "msg": "success", "subMsg": "the real reason"})

    with pytest.raises(aiohttp.ClientResponseError) as exc:
        await vivo.get_app_detail("org.mozilla.firefox")

    assert exc.value.message == "the real reason"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,expected_message",
    (
        pytest.param({"message": "Bad Gateway"}, "Bad Gateway", id="message_key"),
        pytest.param({"unexpected": "shape"}, "Internal Server Error", id="unrecognised_body"),
        pytest.param(["not", "a", "dict"], "Internal Server Error", id="json_list"),
    ),
)
async def test_error_bodies_without_a_vivo_envelope(vivo, responses_mock, payload, expected_message):
    """A gateway or proxy error has no vivo envelope. The error handler has to surface the
    HTTP failure rather than blow up reaching for a key that isn't there."""
    responses_mock.post(ROUTER_URL, status=500, payload=payload)

    with pytest.raises(aiohttp.ClientResponseError) as exc:
        await vivo.get_app_detail("org.mozilla.firefox")

    assert exc.value.status == 500
    assert exc.value.message == expected_message


@pytest.mark.asyncio
async def test_non_json_error_body_defers_to_aiohttp(vivo, responses_mock):
    responses_mock.post(ROUTER_URL, status=502, body="<html>gateway down</html>")

    with pytest.raises(aiohttp.ClientResponseError) as exc:
        await vivo.get_app_detail("org.mozilla.firefox")

    assert exc.value.status == 502


# The sandbox gateway wraps a whole documented envelope inside another one, so the payload
# arrives at `data.data` and the per-call result code at `data.code`.
def _nested(inner_data, inner_code="0", inner_msg=None):
    return {
        "data": {"data": inner_data, "code": inner_code, "msg": inner_msg, "success": inner_code == "0"},
        "code": "0",
        "msg": "success",
        "subCode": "0",
        "subMsg": "success",
        "success": True,
    }


def test_response_data_reads_a_flat_envelope():
    body = success({"serialNumber": "flat-1"})

    assert response_data(body)["serialNumber"] == "flat-1"


def test_response_data_reads_a_nested_envelope():
    """The sandbox nests the envelope, so the payload arrives one level deeper than
    documented."""
    body = _nested({"packageName": "org.mozilla.firefox", "serialNumber": "382bad23d29fb36967ffa6b898f1318d"})

    assert response_data(body)["serialNumber"] == "382bad23d29fb36967ffa6b898f1318d"


@pytest.mark.parametrize(
    "body",
    (
        pytest.param(success(None), id="null_data"),
        pytest.param(success({"packageName": "org.mozilla.firefox", "languageCodes": ["en_in"]}), id="app_detail_payload"),
        pytest.param({"code": "0", "data": {"data": "no code key"}}, id="payload_with_a_data_key_but_no_code"),
    ),
)
def test_a_flat_payload_is_never_mistaken_for_a_nested_envelope(body):
    """Only a `data` carrying a `code` of its own is unwrapped. A documented payload has
    no `code`, so anything looser would start eating real payloads."""
    assert unwrap_nested_envelope(body) is body


def test_a_failure_in_the_inner_envelope_is_raised():
    """The outer envelope reports success while the inner one carries the real failure."""
    body = _nested(None, inner_code="A0113", inner_msg="The uploaded APK package name is not consistent")

    with pytest.raises(VivoException, match="not consistent"):
        raise_for_response_code(body)


def test_a_nested_failure_carrying_no_payload_is_raised():
    """A vivo failure reports itself in `subCode`/`subMsg` and has no `data` of its own,
    so the unwrap keys on the inner `code` alone. Requiring a `data` beside it left the
    inner `subCode` unread, which is the refused-publication-reads-as-success trap."""
    body = {
        "data": {"code": "0", "subCode": "A0305", "msg": "success", "subMsg": "The app is under review", "success": True},
        "code": "0",
        "msg": "success",
        "success": True,
    }

    with pytest.raises(VivoUpdateException, match="already under review"):
        raise_for_response_code(body)


@pytest.mark.asyncio
async def test_upload_accepts_a_nested_envelope(vivo, responses_mock, apk_path):
    """End to end: the sandbox shape must produce a serial number, not an exception."""
    import hashlib

    with open(apk_path, "rb") as fh:
        file_md5 = hashlib.md5(fh.read()).hexdigest()
    responses_mock.post(ROUTER_URL, payload=_nested({"packageName": "org.mozilla.firefox", "fileMd5": file_md5, "serialNumber": "SN-nested"}))

    result = await vivo.upload_apk("org.mozilla.firefox", apk_path, "firefox.apk")

    assert result["serialNumber"] == "SN-nested"
