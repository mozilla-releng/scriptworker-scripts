import asyncio
import os
import pytest
import tempfile


def read_file(path):
    with open(path, 'r') as fh:
        return fh.read()


PUB_KEY = read_file(os.path.join(os.path.dirname(__file__), "id_rsa.pub"))


def noop_sync(*args, **kwargs):
    pass


async def noop_async(*args, **kwargs):
    pass


@pytest.yield_fixture(scope='function')
def tmpdir():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.yield_fixture(scope='function')
def event_loop():
    """Create an instance of the default event loop for each test case.
    From https://github.com/pytest-dev/pytest-asyncio/issues/29#issuecomment-226947296
    """
    policy = asyncio.get_event_loop_policy()
    res = policy.new_event_loop()
    asyncio.set_event_loop(res)
    res._close = res.close
    res.close = lambda: None

    yield res

    res._close()
