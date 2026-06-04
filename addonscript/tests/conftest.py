import inspect
import tempfile
from unittest.mock import Mock

import aiohttp
import pytest

from scriptworker.context import Context


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
def tmpdir():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture(scope="function")
def context():
    context = Context()
    context.config = {
        "amo_instances": {
            "project:releng:addons.mozilla.org:server:dev": {"amo_server": "http://some-amo-it.url", "jwt_user": "test-user", "jwt_secret": "secret"}
        }
    }
    context.task = {"scopes": ["project:releng:addons.mozilla.org:server:dev"]}
    return context
