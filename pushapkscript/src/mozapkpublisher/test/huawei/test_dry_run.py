import pytest
from mozapkpublisher.huawei_api import HuaweiAppGallery


@pytest.mark.asyncio
async def test_huawei_dry_run(responses_mock):
    # Having the `responses_mock` fixture in the test makes sure that this whole test doesn't try to contact any server
    credentials = {"key_id": "k", "sub_account": "s", "private_key": "x"}
    async with HuaweiAppGallery(credentials, dry_run=True) as huawei:
        await huawei.upload_apks('org.mozilla.firefox', [], None)
