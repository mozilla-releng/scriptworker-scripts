import functools
import inspect
import json
from unittest.mock import Mock

import aiohttp
import mock
import pytest
import pytest_asyncio
from scriptworker.context import Context

from . import get_fake_valid_config, get_fake_valid_task


# Cribbed from https://github.com/j7an/dep-rank/pull/123
# aiohttp 3.14 added a required keyword-only ``stream_writer`` argument to
# ``ClientResponse.__init__``. aioresponses (<=0.7.8) builds mocked responses
# without it, so every mocked request raises ``TypeError: ... missing 1
# required keyword-only argument: 'stream_writer'``. aiohttp only reads
# ``stream_writer.output_size``, so a ``Mock(output_size=0)`` suffices.
#
# This mirrors the upstream fix (aioresponses#288, tracking aioresponses#289).
# The signature guard makes it a no-op on aiohttp < 3.14 and once aioresponses
# ships a release that supplies the argument itself; remove this shim then.
_response_init = aiohttp.ClientResponse.__init__
if "stream_writer" in inspect.signature(_response_init).parameters:

    def _patched_response_init(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs.setdefault("stream_writer", Mock(output_size=0))
        _response_init(self, *args, **kwargs)

    aiohttp.ClientResponse.__init__ = _patched_response_init


@pytest.fixture(scope="function")
def context():
    context = Context()
    context.task = get_fake_valid_task()
    context.config = get_fake_valid_config()
    context.release_props = context.task["payload"]["releaseProperties"]
    context.release_props["stage_platform"] = context.release_props["platform"]
    context.resource_type = "bucket"
    context.resource = "nightly"
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

    def release(self):
        return

    async def read(self, *args):
        if self.resp:
            return self.resp.pop(0)


async def _fake_request(resp_status, method, url, *args, **kwargs):
    resp = FakeResponse(method, url, status=resp_status)
    resp._history = (FakeResponse(method, url, status=302),)
    return resp


@pytest_asyncio.fixture(scope="function")
async def fake_session():
    session = aiohttp.ClientSession()
    session._request = functools.partial(_fake_request, 200)
    yield session
    await session.close()


@pytest_asyncio.fixture(scope="function")
async def fake_session_500():
    session = aiohttp.ClientSession()
    session._request = functools.partial(_fake_request, 500)
    yield session
    await session.close()
