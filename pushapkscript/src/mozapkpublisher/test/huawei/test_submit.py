import pytest

from contextlib import nullcontext as does_not_raise
from .common import basic_auth_headers
from mozapkpublisher.huawei_api.error import HuaweiAuthenticationException


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "release_type",
    (1, 2),
)
@pytest.mark.parametrize(
    "status,response,expectation",
    (
        pytest.param(
            401,
            {"ret": {"code": 102, "msg": "Invalid accessToken"}},
            pytest.raises(HuaweiAuthenticationException, match="Invalid accessToken"),
        ),
        pytest.param(
            200,
            {"ret": {"code": 0, "msg": "ok"}},
            does_not_raise(),
        ),
    ),
)
async def test_submit_app(huawei, responses_mock, release_type, status, response, expectation):
    responses_mock.post(
        f"https://connect-api.cloud.huawei.com/api/publish/v2/app-submit?appId=appid-1&releaseType={release_type}",
        status=status,
        payload=response,
    )

    with expectation:
        await huawei.submit_app("appid-1", release_type=release_type)

        responses_mock.assert_called_with(
            url="https://connect-api.cloud.huawei.com/api/publish/v2/app-submit",
            method="POST",
            params={"appId": "appid-1", "releaseType": release_type},
            headers=basic_auth_headers(),
        )
