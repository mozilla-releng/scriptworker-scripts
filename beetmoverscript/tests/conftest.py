import functools
import json

import aiohttp
import mock
import pytest
import pytest_asyncio
from scriptworker.context import Context

from . import get_fake_valid_config, get_fake_valid_task


@pytest.fixture(scope="function")
def context():
    context = Context()
    context.task = get_fake_valid_task()
    context.config = get_fake_valid_config()
    context.release_props = context.task["payload"]["releaseProperties"]
    context.release_props["stage_platform"] = context.release_props["platform"]
    context.resource_type = "bucket"
    context.bucket = "nightly"
    context.action = "push-to-nightly"
    yield context


class FakeResponse(aiohttp.client_reqrep.ClientResponse):
    """Integration tests allow us to test everything's hooked up to aiohttp
    correctly.  When we don't want to actually hit an external url, have
    the aiohttp session's _request method return a FakeResponse.
    """

    def __init__(self, *args, status=200, payload=None, **kwargs):
        self._connection = mock.MagicMock()
        self._payload = payload or {}
        self.status = status
        self._headers = {"content-type": "application/json"}
        self._cache = {}
        self._loop = mock.MagicMock()
        self.content = self
        self.resp = [b"asdf", b"asdf"]
        self._url = args[1]
        self._history = ()

    async def text(self, *args, **kwargs):
        return json.dumps(self._payload)

    async def json(self, *args, **kwargs):
        return self._payload

    async def release(self):
        return

    async def read(self, *args):
        if self.resp:
            return self.resp.pop(0)


async def _fake_request(resp_status, method, url, *args, **kwargs):
    resp = FakeResponse(method, url, status=resp_status)
    resp._history = (FakeResponse(method, url, status=302),)
    return resp


@pytest.mark.asyncio
@pytest_asyncio.fixture(scope="function")
async def fake_session():
    session = aiohttp.ClientSession()
    session._request = functools.partial(_fake_request, 200)
    yield session
    await session.close()


@pytest.mark.asyncio
@pytest_asyncio.fixture(scope="function")
async def fake_session_500():
    session = aiohttp.ClientSession()
    session._request = functools.partial(_fake_request, 500)
    yield session
    await session.close()
