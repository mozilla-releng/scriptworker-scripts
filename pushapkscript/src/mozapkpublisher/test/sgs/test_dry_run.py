import pytest
from mozapkpublisher.sgs_api import SamsungGalaxyStore


@pytest.mark.asyncio
async def test_sgs_dry_run(responses_mock):
    # Having the `responses_mock` fixture in the test makes sure that this whole test doesn't try to contact any server
    async with SamsungGalaxyStore("service_account_id", "access_token", dry_run=True) as sgs:
        await sgs.upload_apks('org.mozilla.firefox', [], None)
