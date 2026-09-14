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
            {"resultCode": "0000", "resultMessage": "Ok", "data": {"binarySeq": "3"}},
            does_not_raise(),
        ),
    ),
)
async def test_add_binary(sgs, responses_mock, status, response, expectation):
    responses_mock.post(
        "https://devapi.samsungapps.com/seller/v2/content/binary",
        status=status,
        payload=response,
    )

    with expectation as exc:
        res = await sgs.add_binary("0123456", "file-key", "N")

    responses_mock.assert_called_with(
        url="https://devapi.samsungapps.com/seller/v2/content/binary",
        method="POST",
        headers=basic_auth_headers(),
        json={
            "contentId": "0123456",
            "filekey": "file-key",
            "gms": "N",
        },
    )

    if exc is None:
        assert res["resultCode"] == "0000"
        assert res["data"]["binarySeq"] == "3"


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
            {"resultCode": "0000", "resultMessage": "Ok"},
            does_not_raise(),
        ),
    ),
)
async def test_delete_binary(sgs, responses_mock, status, response, expectation):
    responses_mock.delete(
        "https://devapi.samsungapps.com/seller/v2/content/binary?contentId=0123456&binarySeq=1",
        status=status,
        payload=response,
    )

    with expectation as exc:
        res = await sgs.delete_binary("0123456", "1")

    responses_mock.assert_called_with(
        url="https://devapi.samsungapps.com/seller/v2/content/binary",
        method="DELETE",
        headers=basic_auth_headers(),
        params={"contentId": "0123456", "binarySeq": "1"},
    )

    if exc is None:
        assert res["resultCode"] == "0000"
        assert res["resultMessage"] == "Ok"
