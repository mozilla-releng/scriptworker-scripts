import os
import tempfile

import pytest
import pytest_asyncio

from mozapkpublisher.vivo_api import VivoAppStoreApi

# Note: `responses_mock` is provided by `mozapkpublisher.tests.sgs.fixtures` which
# is also registered as a pytest plugin in `conftest.py`. Don't redeclare it here.

ACCESS_KEY = "test-access-key"
ACCESS_SECRET = "test-access-secret"


@pytest_asyncio.fixture
async def vivo():
    async with VivoAppStoreApi(ACCESS_KEY, ACCESS_SECRET) as vivo:
        yield vivo


@pytest.fixture
def apk_path():
    """A small fake .apk file on disk; yields its path and cleans up afterwards."""
    with tempfile.NamedTemporaryFile("wb", suffix=".apk", delete=False) as tmp:
        tmp.write(b"x" * 10)
        path = tmp.name
    try:
        yield path
    finally:
        os.unlink(path)
