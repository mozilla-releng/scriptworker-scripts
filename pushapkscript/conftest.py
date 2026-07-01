import inspect
from unittest.mock import Mock
import aiohttp

pytest_plugins = ["mozapkpublisher.test.sgs.fixtures"]


# Fix copied from https://github.com/mozilla-releng/simple-github/commit/2935970b67423f2492ec5e74d95012e39a12b2eb
# TODO: Remove this once https://github.com/pnuckowski/aioresponses/issues/289 is fixed
_response_init = aiohttp.ClientResponse.__init__
if "stream_writer" in inspect.signature(_response_init).parameters:

    def _patched_response_init(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs.setdefault("stream_writer", Mock(output_size=0))
        _response_init(self, *args, **kwargs)

    aiohttp.ClientResponse.__init__ = _patched_response_init
