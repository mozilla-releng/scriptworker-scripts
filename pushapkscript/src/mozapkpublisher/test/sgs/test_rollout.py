import pytest

from contextlib import nullcontext as does_not_raise
from .common import basic_auth_headers
from mozapkpublisher.sgs_api.error import SgsAuthenticationException


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,response,expectation",
    (
        pytest.param(
            401,
            {"code": "AUTH_REQUIRE", "message": "Invalid accessToken", "from": "asgw"},
            pytest.raises(SgsAuthenticationException, match="Invalid accessToken"),
        ),
        pytest.param(
            401,
            {
                "code": "AUTH_REQUIRE",
                "message": "Not found serviceAccount by serviceAccountId",
                "from": "asgw",
            },
            pytest.raises(SgsAuthenticationException, match="Not found serviceAccount"),
        ),
        pytest.param(
            200,
            {"resultCode": "0000", "resultMessage": "Ok", "data": {}},
            does_not_raise(),
        ),
    ),
)
async def test_enable_staged_rollout(
    sgs, responses_mock, status, response, expectation
):
    responses_mock.put(
        "https://devapi.samsungapps.com/seller/v2/content/stagedRolloutRate",
        status=status,
        payload=response,
    )
    with expectation as exc:
        res = await sgs.enable_staged_rollout("0123456", 10)

    responses_mock.assert_called_with(
        url="https://devapi.samsungapps.com/seller/v2/content/stagedRolloutRate",
        method="PUT",
        headers=basic_auth_headers(),
        json={
            "contentId": "0123456",
            "function": "ENABLE_ROLLOUT",
            "appStatus": "REGISTRATION",
            "rolloutRate": 10,
        },
    )

    if exc is None:
        assert res["resultCode"] == "0000"
        assert res["resultMessage"] == "Ok"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,response,expectation",
    (
        pytest.param(
            401,
            {"code": "AUTH_REQUIRE", "message": "Invalid accessToken", "from": "asgw"},
            pytest.raises(SgsAuthenticationException, match="Invalid accessToken"),
        ),
        pytest.param(
            401,
            {
                "code": "AUTH_REQUIRE",
                "message": "Not found serviceAccount by serviceAccountId",
                "from": "asgw",
            },
            pytest.raises(SgsAuthenticationException, match="Not found serviceAccount"),
        ),
        pytest.param(
            200,
            {"resultCode": "0000", "resultMessage": "Ok", "data": {}},
            does_not_raise(),
        ),
    ),
)
async def test_add_binary_to_staged_rollout(
    sgs, responses_mock, status, response, expectation
):
    responses_mock.put(
        "https://devapi.samsungapps.com/seller/v2/content/stagedRolloutBinary",
        status=status,
        payload=response,
    )

    with expectation as exc:
        res = await sgs.add_binary_to_staged_rollout("0123456", "123")

    responses_mock.assert_called_with(
        url="https://devapi.samsungapps.com/seller/v2/content/stagedRolloutBinary",
        method="PUT",
        json={"contentId": "0123456", "function": "ADD", "binarySeq": "123"},
        headers=basic_auth_headers(),
    )

    if exc is None:
        assert res["resultCode"] == "0000"
        assert res["resultMessage"] == "Ok"
