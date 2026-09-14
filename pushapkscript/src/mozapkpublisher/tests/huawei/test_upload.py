import hashlib
import pytest
import unittest

from contextlib import nullcontext as does_not_raise
from .common import basic_auth_headers, form_fields, recorded_calls
from mozapkpublisher.huawei_api import HuaweiAppGallery
from mozapkpublisher.huawei_api.error import (
    HuaweiAuthenticationException,
    HuaweiUploadException,
)

CREDENTIALS = {"key_id": "k", "sub_account": "s", "private_key": "x"}
UPLOAD_URL = "https://upload.example/foo"
DEST_URL = "https://cdn.example/dest"


def _sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


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
                                "fileDestUlr": "https://cdn.example/dest",
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
        assert res["fileDestUlr"] == "https://cdn.example/dest"


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "file_info,expected",
    (
        pytest.param({"fileDestUlr": DEST_URL, "size": 10}, DEST_URL, id="huawei_misspelling"),
        pytest.param({"fileDestUrl": DEST_URL, "size": 10}, DEST_URL, id="corrected_spelling"),
        pytest.param({"size": 10}, None, id="neither_spelling"),
    ),
)
async def test_upload_file_reads_the_destination_url(responses_mock, apk_path, mock_jwt, file_info, expected):
    """The upload response misspells the destination URL key as `fileDestUlr`, while the
    `app-file-info` request that consumes it uses `fileDestUrl`. Accept both, and fail with
    a message naming the response rather than a bare KeyError when neither is present."""
    responses_mock.get(
        "https://connect-api.cloud.huawei.com/api/publish/v2/upload-url"
        f"?appId=appid-1&suffix=apk&releaseType=1&sha256={_sha256(apk_path)}",
        payload={"ret": {"code": 0, "msg": "ok"}, "uploadUrl": UPLOAD_URL, "authCode": "ac"},
    )
    responses_mock.post(
        UPLOAD_URL,
        payload={"result": {"UploadFileRsp": {"ifSuccess": 1, "fileInfoList": [file_info]}}},
    )

    async with HuaweiAppGallery(CREDENTIALS) as huawei:
        if expected is None:
            with pytest.raises(HuaweiUploadException, match="file destination URL"):
                await huawei.upload_file("appid-1", apk_path, "fenix-x86-1.0.apk")
        else:
            assert await huawei.upload_file("appid-1", apk_path, "fenix-x86-1.0.apk") == expected


@pytest.mark.asyncio
async def test_upload_file_multipart_body(huawei, responses_mock, apk_path):
    """The multipart form must carry the authCode handed back by `get_upload_url` and the
    per-APK filename that `build_apk_file_name` produces -- uploading every architecture
    under one name is what caused the "binary already in use" failures of Bug 1974870."""
    responses_mock.post(
        UPLOAD_URL,
        payload={"result": {"UploadFileRsp": {"ifSuccess": 1, "fileInfoList": [{"fileDestUlr": DEST_URL, "size": 10}]}}},
    )

    await huawei.upload_file(UPLOAD_URL, "auth-code-xyz", apk_path, "fenix-x86-1.0.apk")

    calls = recorded_calls(responses_mock, "POST", UPLOAD_URL)
    assert len(calls) == 1
    fields = form_fields(calls[0].kwargs["data"])

    assert fields["authCode"] == (None, "auth-code-xyz")
    assert fields["fileCount"] == (None, "1")
    assert fields["file"][0] == "fenix-x86-1.0.apk"


@pytest.mark.asyncio
async def test_upload_file_with_empty_file_info_list(huawei, responses_mock, apk_path):
    responses_mock.post(
        UPLOAD_URL,
        payload={"result": {"UploadFileRsp": {"ifSuccess": 1, "fileInfoList": []}}},
    )

    with pytest.raises(HuaweiUploadException, match="didn't contain a fileInfoList entry"):
        await huawei.upload_file(UPLOAD_URL, "auth-code-xyz", apk_path, "fenix-x86-1.0.apk")
