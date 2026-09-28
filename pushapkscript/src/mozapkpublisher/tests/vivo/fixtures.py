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


def apk_metadata(architecture="arm64-v8a", version_name="116.0"):
    """Metadata shaped like what `extract_and_check_apks_metadata` hands `push_apk`."""
    return {"package_name": "org.mozilla.firefox", "architecture": architecture, "version_name": version_name}


@pytest.fixture
def apk(apk_path):
    """An open fake APK, shaped like the `(file, metadata)` pairs `push_apk` passes in."""
    with open(apk_path, "rb") as fd:
        yield (fd, apk_metadata())
