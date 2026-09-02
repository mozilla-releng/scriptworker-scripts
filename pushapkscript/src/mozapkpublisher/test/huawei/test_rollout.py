import hashlib

from datetime import datetime, timezone
from unittest import mock

import pytest

import mozapkpublisher.huawei_api
from mozapkpublisher.huawei_api import (
    HuaweiAppGallery,
    PHASED_ROLLOUT_WINDOW,
    RELEASE_TYPE_FULL_ROLLOUT,
    RELEASE_TYPE_PHASED_ROLLOUT,
    build_phased_release,
)
from mozapkpublisher.huawei_api.error import HuaweiUpdateException
from .common import basic_auth_headers

APP_ID = "appid-1"
PACKAGE_NAME = "org.mozilla.firefox"
UPLOAD_URL = "https://upload.example/foo"
FILE_DEST_URL = "https://cdn.example/dest"
CREDENTIALS = {"key_id": "k", "sub_account": "s", "private_key": "x"}

# `datetime.now` is patched to this so the phased-release window is assertable.
FROZEN_NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.fixture
def frozen_now():
    with mock.patch.object(mozapkpublisher.huawei_api, "datetime") as mocked_datetime:
        mocked_datetime.now.return_value = FROZEN_NOW
        yield FROZEN_NOW


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


def _register_upload_chain(responses_mock, sha256, *, submit_release_type=None, apk_count=1):
    """Register the mocked happy-path responses for the full `upload_apks` flow.

    The per-APK steps (upload-url, upload) are registered `apk_count` times; the
    per-release steps (appid-list, app-file-info, app-submit) exactly once.
    """
    responses_mock.get(
        f"https://connect-api.cloud.huawei.com/api/publish/v2/appid-list?packageName={PACKAGE_NAME}",
        payload={"ret": {"code": 0, "msg": "ok"}, "appids": [{"key": "Firefox", "value": APP_ID}]},
    )
    responses_mock.get(
        f"https://connect-api.cloud.huawei.com/api/publish/v2/upload-url?appId={APP_ID}&suffix=apk&releaseType=1&sha256={sha256}",
        payload={"ret": {"code": 0, "msg": "ok"}, "uploadUrl": UPLOAD_URL, "authCode": "ac"},
        repeat=apk_count,
    )
    responses_mock.post(
        UPLOAD_URL,
        payload={"result": {"UploadFileRsp": {"ifSuccess": 1, "fileInfoList": [{"fileDestUlr": FILE_DEST_URL, "size": 10}]}}},
        repeat=apk_count,
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
    "rollout_rate,expected_release_type,expected_body",
    [
        (None, RELEASE_TYPE_FULL_ROLLOUT, {}),
        (
            10,
            RELEASE_TYPE_PHASED_ROLLOUT,
            {
                "json": {
                    "phasedReleaseStartTime": "2026-01-02T03:04:05+0000",
                    "phasedReleaseEndTime": "2026-01-09T03:04:05+0000",
                    "phasedReleasePercent": "10.00",
                    "phasedReleaseDescription": "Phased rollout to 10.00% of users",
                }
            },
        ),
    ],
    ids=["full_rollout", "phased_rollout"],
)
async def test_submit_uses_full_or_phased_release_type(
    responses_mock, apk_path, mock_jwt, frozen_now, rollout_rate, expected_release_type, expected_body
):
    """submit uses a full release (releaseType=1) with no body when no rollout rate is set,
    and a phased release (releaseType=3) carrying the mandatory phased-release body when one
    is set."""
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
        **expected_body,
    )


@pytest.mark.asyncio
async def test_upload_apks_binds_every_architecture_to_the_release(responses_mock, apk_path, mock_jwt):
    """Each uploaded APK must end up in the single app-file-info call that binds the
    binaries to the release, otherwise a multi-architecture release ships incomplete."""
    architectures = ("arm64-v8a", "armeabi-v7a", "x86_64")
    _register_upload_chain(responses_mock, _sha256(apk_path), apk_count=len(architectures))

    async with HuaweiAppGallery(CREDENTIALS) as huawei:
        await huawei.upload_apks(
            PACKAGE_NAME,
            [(_FileDescriptor(apk_path), _apk_metadata(architecture=arch)) for arch in architectures],
            None,
        )

    responses_mock.assert_called_with(
        url="https://connect-api.cloud.huawei.com/api/publish/v2/app-file-info",
        method="PUT",
        params={"appId": APP_ID},
        headers=basic_auth_headers(),
        json={
            "fileType": 5,
            "files": [
                {"fileName": f"{PACKAGE_NAME}-{arch}-1.0.apk", "fileDestUrl": FILE_DEST_URL}
                for arch in architectures
            ],
        },
    )


def test_release_type_constants_match_the_documented_api_values():
    """AppGallery accepts releaseType 1 (entire network) and 3 (by phase); there is no 2.

    The tests above use these constants on both the mock and the assertion side, so they
    would pass with any value. Pinning the literals here is what actually holds the wire
    contract in place.

    https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-app-submit-0000001158245061
    """
    assert RELEASE_TYPE_FULL_ROLLOUT == 1
    assert RELEASE_TYPE_PHASED_ROLLOUT == 3


def test_build_phased_release():
    body = build_phased_release(25.5, start_time=FROZEN_NOW)

    assert body == {
        "phasedReleaseStartTime": "2026-01-02T03:04:05+0000",
        "phasedReleaseEndTime": "2026-01-09T03:04:05+0000",
        "phasedReleasePercent": "25.50",
        "phasedReleaseDescription": "Phased rollout to 25.50% of users",
    }

    start = datetime.strptime(body["phasedReleaseStartTime"], "%Y-%m-%dT%H:%M:%S%z")
    end = datetime.strptime(body["phasedReleaseEndTime"], "%Y-%m-%dT%H:%M:%S%z")
    assert end - start == PHASED_ROLLOUT_WINDOW


@pytest.mark.parametrize("rollout_rate", (0, -1, 100.01, 150))
def test_build_phased_release_rejects_out_of_range_rate(rollout_rate):
    with pytest.raises(HuaweiUpdateException, match="Rollout percentage must be in"):
        build_phased_release(rollout_rate, start_time=FROZEN_NOW)


@pytest.mark.asyncio
async def test_upload_apks_reports_what_it_did(responses_mock, apk_path, mock_jwt, caplog):
    """A successful run used to print nothing at all after the APK checks, so an operator
    could not tell an upload from a no-op."""
    _register_upload_chain(responses_mock, _sha256(apk_path))

    with caplog.at_level("INFO", logger="mozapkpublisher.huawei_api"):
        async with HuaweiAppGallery(CREDENTIALS) as huawei:
            await huawei.upload_apks(
                PACKAGE_NAME, [(_FileDescriptor(apk_path), _apk_metadata())], None
            )

    messages = [record.getMessage() for record in caplog.records]
    assert any(APP_ID in m and PACKAGE_NAME in m for m in messages), messages
    assert any("Uploaded {}-arm64-v8a-1.0.apk".format(PACKAGE_NAME) in m for m in messages), messages
    assert any(m.startswith("Bound 1 binaries") for m in messages), messages
    # Not submitting is the surprising outcome, so it must be loud.
    assert any("NOT submitted" in m for m in messages), messages


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rollout_rate,expected",
    (
        pytest.param(None, "FULL release to all users", id="full"),
        pytest.param(10, "PHASED release to 10% of users over 7 days", id="phased"),
    ),
)
async def test_release_type_is_announced_before_submitting(
    responses_mock, apk_path, mock_jwt, frozen_now, caplog, rollout_rate, expected
):
    """The release type has to be logged before the submission goes out, so an operator who
    picked the wrong one can still interrupt."""
    release_type = RELEASE_TYPE_FULL_ROLLOUT if rollout_rate is None else RELEASE_TYPE_PHASED_ROLLOUT
    _register_upload_chain(responses_mock, _sha256(apk_path), submit_release_type=release_type)

    with caplog.at_level("INFO", logger="mozapkpublisher.huawei_api"):
        async with HuaweiAppGallery(CREDENTIALS) as huawei:
            await huawei.upload_apks(
                PACKAGE_NAME, [(_FileDescriptor(apk_path), _apk_metadata())], rollout_rate, submit=True
            )

    messages = [record.getMessage() for record in caplog.records]
    announcements = [i for i, m in enumerate(messages) if expected in m]
    assert announcements, messages
    submitted = [i for i, m in enumerate(messages) if m.startswith("Submitted app")]
    assert submitted and announcements[0] < submitted[0], messages
