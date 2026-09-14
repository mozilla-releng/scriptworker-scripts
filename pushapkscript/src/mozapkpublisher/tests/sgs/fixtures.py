from aioresponses import aioresponses
from mozapkpublisher.sgs_api import SamsungGalaxyApi

import pytest
import pytest_asyncio


@pytest.fixture
def responses_mock():
    with aioresponses() as m:
        yield m


@pytest_asyncio.fixture
async def sgs():
    async with SamsungGalaxyApi("service_account_id", "access_token") as sgs:
        yield sgs
