import aiohttp
import pytest

from mozapkpublisher.huawei_api import HuaweiAppGallery
from mozapkpublisher.huawei_api.error import (
    HuaweiAuthorizationException,
    HuaweiException,
)
from mozapkpublisher.huawei_api.utils import RESULT_CODES_DOC_URL, raise_for_ret_code

CREDENTIALS = {"key_id": "k", "sub_account": "s", "private_key": "x"}
APP_SUBMIT_URL = "https://connect-api.cloud.huawei.com/api/publish/v2/app-submit?appId=appid-1&releaseType=1"


@pytest.mark.parametrize(
    "body",
    (
        pytest.param({"ret": {"code": 0, "msg": "ok"}}, id="success_code"),
        pytest.param({"ret": {}}, id="empty_envelope"),
        pytest.param({"appids": []}, id="no_envelope"),
    ),
)
def test_raise_for_ret_code_accepts(body):
    assert raise_for_ret_code(body) is None


def test_raise_for_ret_code_rejects_a_non_zero_code():
    with pytest.raises(HuaweiException) as exc:
        raise_for_ret_code({"ret": {"code": 204144660, "msg": "app not exist"}})

    message = str(exc.value)
    assert "204144660" in message
    assert "app not exist" in message
    assert RESULT_CODES_DOC_URL in message


@pytest.mark.asyncio
async def test_in_band_error_on_an_http_200_is_raised(huawei, responses_mock):
    """AppGallery reports many failures as HTTP 200 with a non-zero `ret.code`. Without
    the in-band check a failed submit reads as a successful one."""
    responses_mock.post(
        APP_SUBMIT_URL,
        status=200,
        payload={"ret": {"code": 204144660, "msg": "app not exist"}},
    )

    with pytest.raises(HuaweiException, match="app not exist"):
        await huawei.submit_app("appid-1")


@pytest.mark.asyncio
async def test_403_raises_an_authorization_error(huawei, responses_mock):
    """A 403 means the service account lacks the publishing role. Reporting it as an
    authentication failure would send operators off rotating a healthy key."""
    responses_mock.post(
        APP_SUBMIT_URL,
        status=403,
        payload={"ret": {"code": 105, "msg": "Insufficient permission"}},
    )

    with pytest.raises(HuaweiAuthorizationException, match="Insufficient permission"):
        await huawei.submit_app("appid-1")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,expected_message",
    (
        pytest.param({"message": "Bad Gateway"}, "Bad Gateway", id="message_key"),
        pytest.param({"unexpected": "shape"}, "Internal Server Error", id="unrecognised_body"),
        pytest.param(["not", "a", "dict"], "Internal Server Error", id="json_list"),
    ),
)
async def test_error_bodies_without_a_ret_envelope(huawei, responses_mock, payload, expected_message):
    """A gateway or proxy error has no `ret` envelope. The error handler has to surface the
    HTTP failure rather than blow up reaching for a key that isn't there."""
    responses_mock.post(APP_SUBMIT_URL, status=500, payload=payload)

    with pytest.raises(aiohttp.ClientResponseError) as exc:
        await huawei.submit_app("appid-1")

    assert exc.value.status == 500
    assert exc.value.message == expected_message


@pytest.mark.asyncio
async def test_non_json_error_body_defers_to_aiohttp(huawei, responses_mock):
    responses_mock.post(APP_SUBMIT_URL, status=502, body="<html>gateway down</html>")

    with pytest.raises(aiohttp.ClientResponseError) as exc:
        await huawei.submit_app("appid-1")

    assert exc.value.status == 502


@pytest.mark.asyncio
async def test_in_band_error_aborts_before_submitting(responses_mock, mock_jwt):
    """An in-band failure part way through `upload_apks` must stop the flow, not let it
    carry on to app-submit."""
    responses_mock.get(
        "https://connect-api.cloud.huawei.com/api/publish/v2/appid-list?packageName=org.mozilla.firefox",
        payload={"ret": {"code": 204144660, "msg": "app not exist"}, "appids": []},
    )

    async with HuaweiAppGallery(CREDENTIALS) as huawei:
        with pytest.raises(HuaweiException, match="app not exist"):
            await huawei.upload_apks("org.mozilla.firefox", [], None, submit=True)
