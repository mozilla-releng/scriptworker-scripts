import pytest

from mozapkpublisher.huawei_api import HuaweiAppGallery
from mozapkpublisher.huawei_api.error import HuaweiUpdateException

PACKAGE_NAME = "org.mozilla.firefox"
CREDENTIALS = {"key_id": "k", "sub_account": "s", "private_key": "x"}
APPID_LIST_URL = f"https://connect-api.cloud.huawei.com/api/publish/v2/appid-list?packageName={PACKAGE_NAME}"


@pytest.mark.asyncio
async def test_infer_app_id_from_package_name(responses_mock, mock_jwt):
    """`appid-list` entries are `{"key": <app name>, "value": <app id>}` pairs. The route
    has already filtered on `packageName` and the entries carry no package name of their
    own, so there is nothing to match on client-side."""
    responses_mock.get(
        APPID_LIST_URL,
        payload={"ret": {"code": 0, "msg": "ok"}, "appids": [{"key": "Firefox", "value": "104656999"}]},
    )

    async with HuaweiAppGallery(CREDENTIALS) as huawei:
        assert await huawei.infer_app_id_from_package_name(PACKAGE_NAME) == "104656999"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "appids,expected_message",
    (
        pytest.param([], "Couldn't find an app ID", id="empty_list"),
        pytest.param(None, "Couldn't find an app ID", id="key_absent"),
        pytest.param(
            [{"key": "Firefox", "value": "1"}, {"key": "Firefox Beta", "value": "2"}],
            "Found multiple app IDs",
            id="ambiguous",
        ),
    ),
)
async def test_infer_app_id_from_package_name_failures(responses_mock, mock_jwt, appids, expected_message):
    payload = {"ret": {"code": 0, "msg": "ok"}}
    if appids is not None:
        payload["appids"] = appids
    responses_mock.get(APPID_LIST_URL, payload=payload)

    async with HuaweiAppGallery(CREDENTIALS) as huawei:
        with pytest.raises(HuaweiUpdateException, match=expected_message):
            await huawei.infer_app_id_from_package_name(PACKAGE_NAME)
