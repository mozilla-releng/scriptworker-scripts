from unittest import mock

import os
import tempfile

import pytest
import pytest_asyncio

import mozapkpublisher.huawei_api
from mozapkpublisher.huawei_api import HuaweiAppGalleryApi


# Note: `responses_mock` is provided by `mozapkpublisher.test.sgs.fixtures` which
# is also registered as a pytest plugin in `conftest.py`. Don't redeclare it here.

TEST_CREDENTIALS = {
    "key_id": "test-key-id",
    "sub_account": "test-sub-account",
    "private_key": "unused-because-create_jwt-is-mocked",
}

# The signed JWT is time-based, so tests patch `create_jwt` to return this constant.
# `common.basic_auth_headers` expects the matching `Authorization` header.
MOCK_JWT = "jwt-token"


@pytest.fixture
def mock_jwt():
    with mock.patch.object(mozapkpublisher.huawei_api, "create_jwt", return_value=MOCK_JWT):
        yield MOCK_JWT


@pytest_asyncio.fixture
async def huawei(mock_jwt):
    async with HuaweiAppGalleryApi(TEST_CREDENTIALS) as huawei:
        yield huawei


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
