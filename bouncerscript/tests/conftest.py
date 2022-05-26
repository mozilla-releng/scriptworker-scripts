import asyncio
import functools
import json

import aiohttp
import mock
import pytest
import pytest_asyncio
from scriptworker.context import Context

from . import get_fake_valid_config, get_fake_valid_task

try:
    import yarl

    YARL = True
except ImportError:
    YARL = False


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
        if YARL:
            # fix aiohttp 1.1.0
            self._url_obj = yarl.URL(args[1])

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


@pytest.fixture(scope="function")
def submission_context():
    context = Context()
    context.task = get_fake_valid_task("submission")
    context.config = get_fake_valid_config()

    yield context


@pytest.fixture(scope="function")
def aliases_context():
    context = Context()
    context.task = get_fake_valid_task("aliases")
    context.config = get_fake_valid_config()
    context.server = "project:releng:bouncer:server:production"

    yield context


@pytest.fixture(scope="function")
def locations_context():
    context = Context()
    context.task = get_fake_valid_task("locations")
    context.config = get_fake_valid_config()

    yield context


@pytest_asyncio.fixture(scope="function")
async def fake_ClientError_throwing_session():
    async def _fake_request(method, url, *args, **kwargs):
        raise aiohttp.ClientError

    loop = asyncio.get_event_loop()
    session = aiohttp.ClientSession(loop=loop)
    session._request = _fake_request
    return session


@pytest_asyncio.fixture(scope="function")
async def fake_TimeoutError_throwing_session():
    async def _fake_request(method, url, *args, **kwargs):
        raise aiohttp.ServerTimeoutError

    loop = asyncio.get_event_loop()
    session = aiohttp.ClientSession(loop=loop)
    session._request = _fake_request
    return session
