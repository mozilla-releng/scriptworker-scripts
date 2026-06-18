import pytest
import unittest

from contextlib import nullcontext as does_not_raise
from .common import basic_auth_headers
from mozapkpublisher.huawei_api.error import (
    HuaweiAuthenticationException,
    HuaweiUploadException,
)


@pytest.mark.asyncio
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
            {
                "ret": {"code": 0, "msg": "ok"},
                "uploadUrl": "https://upload.example/foo",
                "chunkUploadUrl": "https://upload.example/foo/chunk",
                "authCode": "auth-code-xyz",
            },
            does_not_raise(),
        ),
    ),
)
async def test_get_upload_url(huawei, responses_mock, status, response, expectation):
    responses_mock.get(
        "https://connect-api.cloud.huawei.com/api/publish/v2/upload-url?appId=appid-1&suffix=apk&releaseType=1",
        status=status,
        payload=response,
    )
    with expectation as exc:
        res = await huawei.get_upload_url("appid-1", suffix="apk", release_type=1)

    responses_mock.assert_called_with(
        url="https://connect-api.cloud.huawei.com/api/publish/v2/upload-url",
        method="GET",
        params={"appId": "appid-1", "suffix": "apk", "releaseType": 1},
        headers=basic_auth_headers(),
    )
    if exc is None:
        assert res["uploadUrl"] == "https://upload.example/foo"
        assert res["authCode"] == "auth-code-xyz"


@pytest.mark.asyncio
async def test_get_upload_url_sends_sha256(huawei, responses_mock):
    responses_mock.get(
        "https://connect-api.cloud.huawei.com/api/publish/v2/upload-url?appId=appid-1&suffix=apk&releaseType=1&sha256=deadbeef",
        payload={"ret": {"code": 0, "msg": "ok"}, "uploadUrl": "https://upload.example/foo", "authCode": "auth-code-xyz"},
    )

    await huawei.get_upload_url("appid-1", suffix="apk", release_type=1, sha256="deadbeef")

    responses_mock.assert_called_with(
        url="https://connect-api.cloud.huawei.com/api/publish/v2/upload-url",
        method="GET",
        params={"appId": "appid-1", "suffix": "apk", "releaseType": 1, "sha256": "deadbeef"},
        headers=basic_auth_headers(),
    )


@pytest.mark.asyncio
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
            {
                "result": {
                    "UploadFileRsp": {
                        "ifSuccess": 1,
                        "fileInfoList": [
                            {
                                "fileDestUlr": "https://cdn.example/dest",
                                "fileDestUrl": "https://cdn.example/dest",
                                "size": 9,
                            }
                        ],
                    }
                }
            },
            pytest.raises(HuaweiUploadException, match="Got 9, expected 10"),
        ),
        pytest.param(
            200,
            {
                "result": {
                    "UploadFileRsp": {
                        "ifSuccess": 1,
                        "fileInfoList": [
                            {
                                "fileDestUrl": "https://cdn.example/dest",
                                "size": 10,
                            }
                        ],
                    }
                }
            },
            does_not_raise(),
        ),
    ),
)
async def test_upload_file(huawei, responses_mock, apk_path, status, response, expectation):
    responses_mock.post(
        "https://upload.example/foo",
        status=status,
        payload=response,
    )

    with expectation as exc:
        res = await huawei.upload_file(
            "https://upload.example/foo", "auth-code-xyz", apk_path, "fenix-x86-1.0.apk"
        )

    responses_mock.assert_called_with(
        url="https://upload.example/foo",
        method="POST",
        headers=basic_auth_headers(),
        data=unittest.mock.ANY,
    )
    if exc is None:
        assert res["fileDestUrl"] == "https://cdn.example/dest"


@pytest.mark.asyncio
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
async def test_update_app_file_info(huawei, responses_mock, status, response, expectation):
    responses_mock.put(
        "https://connect-api.cloud.huawei.com/api/publish/v2/app-file-info?appId=appid-1",
        status=status,
        payload=response,
    )

    files = [
        {"fileName": "fenix-x86-1.0.apk", "fileDestUrl": "https://cdn.example/dest"},
    ]
    with expectation:
        await huawei.update_app_file_info("appid-1", files)

        responses_mock.assert_called_with(
            url="https://connect-api.cloud.huawei.com/api/publish/v2/app-file-info",
            method="PUT",
            params={"appId": "appid-1"},
            headers=basic_auth_headers(),
            json={"fileType": 5, "files": files},
        )
