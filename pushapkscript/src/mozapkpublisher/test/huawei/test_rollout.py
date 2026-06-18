import hashlib

import pytest

from mozapkpublisher.huawei_api import HuaweiAppGallery, RELEASE_TYPE_FULL_ROLLOUT, RELEASE_TYPE_PHASED_ROLLOUT
from .common import basic_auth_headers

APP_ID = "appid-1"
PACKAGE_NAME = "org.mozilla.firefox"
UPLOAD_URL = "https://upload.example/foo"
FILE_DEST_URL = "https://cdn.example/dest"
CREDENTIALS = {"key_id": "k", "sub_account": "s", "private_key": "x"}


def _sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _apk_metadata(version_name="1.0", architecture="arm64-v8a"):
    return {
        "package_name": PACKAGE_NAME,
        "architecture": architecture,
        "version_name": version_name,
        "version_code": 1000,
        "api_level": 21,
    }


class _FileDescriptor:
    """Minimal stand-in for the file object `upload_apks` expects (it only reads `.name`)."""

    def __init__(self, name):
        self.name = name


def _register_upload_chain(responses_mock, sha256, *, submit_release_type=None):
    """Register the mocked happy-path responses for the full `upload_apks` flow."""
    responses_mock.get(
        f"https://connect-api.cloud.huawei.com/api/publish/v2/appid-list?packageName={PACKAGE_NAME}",
        payload={"ret": {"code": 0, "msg": "ok"}, "appids": [{"package": PACKAGE_NAME, "value": APP_ID}]},
    )
    responses_mock.get(
        f"https://connect-api.cloud.huawei.com/api/publish/v2/upload-url?appId={APP_ID}&suffix=apk&releaseType=1&sha256={sha256}",
        payload={"ret": {"code": 0, "msg": "ok"}, "uploadUrl": UPLOAD_URL, "authCode": "ac"},
    )
    responses_mock.post(
        UPLOAD_URL,
        payload={"result": {"UploadFileRsp": {"ifSuccess": 1, "fileInfoList": [{"fileDestUrl": FILE_DEST_URL, "size": 10}]}}},
    )
    responses_mock.put(
        f"https://connect-api.cloud.huawei.com/api/publish/v2/app-file-info?appId={APP_ID}",
        payload={"ret": {"code": 0, "msg": "ok"}},
    )
    if submit_release_type is not None:
        responses_mock.post(
            f"https://connect-api.cloud.huawei.com/api/publish/v2/app-submit?appId={APP_ID}&releaseType={submit_release_type}",
            payload={"ret": {"code": 0, "msg": "ok"}},
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rollout_rate,expected_release_type",
    [(None, RELEASE_TYPE_FULL_ROLLOUT), (10, RELEASE_TYPE_PHASED_ROLLOUT)],
    ids=["full_rollout", "phased_rollout"],
)
async def test_submit_uses_full_or_phased_release_type(responses_mock, apk_path, mock_jwt, rollout_rate, expected_release_type):
    """submit uses a full release (releaseType=1) when no rollout rate is set, and a phased
    release (releaseType=2) when a rollout rate is set."""
    _register_upload_chain(responses_mock, _sha256(apk_path), submit_release_type=expected_release_type)

    async with HuaweiAppGallery(CREDENTIALS) as huawei:
        await huawei.upload_apks(
            PACKAGE_NAME, [(_FileDescriptor(apk_path), _apk_metadata())], rollout_rate, submit=True
        )

    # If submit had used the wrong releaseType the mock above wouldn't match; this
    # makes the asserted releaseType explicit.
    responses_mock.assert_called_with(
        url="https://connect-api.cloud.huawei.com/api/publish/v2/app-submit",
        method="POST",
        params={"appId": APP_ID, "releaseType": expected_release_type},
        headers=basic_auth_headers(),
    )
