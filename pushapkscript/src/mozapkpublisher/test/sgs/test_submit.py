import pytest
import tempfile
import unittest
import uuid

from contextlib import nullcontext as does_not_raise
from .common import basic_auth_headers
from mozapkpublisher.sgs_api.error import (
    SgsAuthenticationException,
    SgsUploadException,
)
from mozapkpublisher.sgs_api.content_info import AppContentInfo


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
            {
                "url": "https://seller.samsungapps.com/galaxyapi/fileUpload",
                "sessionId": "d7ca6869-128e-4bfb-a56d-674d77f08848",
            },
            does_not_raise(),
        ),
    ),
)
async def test_create_session_id(sgs, responses_mock, status, response, expectation):
    responses_mock.post(
        "https://devapi.samsungapps.com/seller/createUploadSessionId",
        status=status,
        payload=response,
    )
    with expectation as exc:
        res = await sgs.create_upload_session_id()

    responses_mock.assert_called_with(
        url="https://devapi.samsungapps.com/seller/createUploadSessionId",
        method="POST",
        headers=basic_auth_headers(),
    )
    if exc is None:
        assert res["sessionId"] == "d7ca6869-128e-4bfb-a56d-674d77f08848"


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
        pytest.param(204, None, does_not_raise()),
    ),
)
async def test_submit_app(sgs, responses_mock, status, response, expectation):
    responses_mock.post(
        "https://devapi.samsungapps.com/seller/contentSubmit",
        status=status,
        payload=response,
    )

    with expectation as exc:
        res = await sgs.submit_app("0123456")

    if exc is None:
        assert res is None


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
            {
                "fileKey": "5d33cb93-b399-41c0-9c41-667946736d09",
                "fileName": "ICON_512x512.png",
                "fileSize": "9",
                "errorCode": None,
                "errorMsg": None,
            },
            pytest.raises(SgsUploadException, match="Got 9, expected 10"),
        ),
        pytest.param(
            200,
            {
                "fileKey": "5d33cb93-b399-41c0-9c41-667946736d09",
                "fileName": "ICON_512x512.png",
                "fileSize": "10",
                "errorCode": None,
                "errorMsg": None,
            },
            does_not_raise(),
        ),
    ),
)
async def test_upload_apk(sgs, responses_mock, status, response, expectation):
    responses_mock.post(
        "https://seller.samsungapps.com/galaxyapi/fileUpload",
        status=status,
        payload=response,
    )

    session_id = uuid.uuid4()
    with tempfile.NamedTemporaryFile("w") as tmp, expectation as exc:
        tmp.write("1" * 10)
        tmp.flush()
        res = await sgs.upload_file(str(session_id), tmp.name, "foobar")

    responses_mock.assert_called_with(
        url="https://seller.samsungapps.com/galaxyapi/fileUpload",
        method="POST",
        headers=basic_auth_headers(),
        data=unittest.mock.ANY,
    )
    if exc is None:
        assert res["fileKey"] == "5d33cb93-b399-41c0-9c41-667946736d09"
        assert res["errorCode"] is None
        assert res["errorMsg"] is None


UPDATE_BASE_PARAMS = {
    "contentId": "foobar",
    "defaultLanguageCode": "EN",
    "paid": "N",
    "publicationType": "03",
    "binaryList": [],
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,params,response,expectation",
    (
        pytest.param(
            401,
            UPDATE_BASE_PARAMS,
            {"code": "AUTH_REQUIRE", "message": "Invalid accessToken", "from": "asgw"},
            pytest.raises(SgsAuthenticationException, match="Invalid accessToken"),
        ),
        pytest.param(
            401,
            UPDATE_BASE_PARAMS,
            {
                "code": "AUTH_REQUIRE",
                "message": "Not found serviceAccount by serviceAccountId",
                "from": "asgw",
            },
            pytest.raises(SgsAuthenticationException, match="Not found serviceAccount"),
        ),
        pytest.param(200, UPDATE_BASE_PARAMS, {}, does_not_raise()),
    ),
)
async def test_update_content_info(
    sgs, responses_mock, status, params, response, expectation
):
    responses_mock.post(
        "https://devapi.samsungapps.com/seller/contentUpdate",
        status=status,
        payload=response,
    )

    with expectation:
        data = AppContentInfo(params)
        await sgs.update_content_info(data)

        expected_extra_fields = {
            "screenshots": None,
            "addLanguage": None,
            "sellCountryList": None,
        }
        expected_json = UPDATE_BASE_PARAMS | expected_extra_fields
        responses_mock.assert_called_with(
            url="https://devapi.samsungapps.com/seller/contentUpdate",
            method="POST",
            headers=basic_auth_headers(),
            json=expected_json,
        )


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
            [
                {
                    "contentName": "app1",
                    "contentId": "0123456",
                    "contentStatus": "FOR_SALE",
                    "standardPrice": "0",
                    "paid": "N",
                    "modifyDate": "2025-04-14 16:03:35.0",
                },
                {
                    "contentName": "app2",
                    "contentId": "0123457",
                    "contentStatus": "FOR_SALE",
                    "standardPrice": "0",
                    "paid": "N",
                    "modifyDate": "2025-04-14 16:03:35.0",
                },
            ],
            does_not_raise(),
        ),
    ),
)
async def test_app_list(sgs, responses_mock, status, response, expectation):
    responses_mock.get(
        "https://devapi.samsungapps.com/seller/contentList",
        status=status,
        payload=response,
    )

    with expectation as exc:
        res = await sgs.app_list()

    if exc is None:
        assert res[0]["contentId"] == "0123456"
        assert len(res) == 2
