import asyncio
import os
import pytest
import tempfile


def read_file(path):
    with open(path, 'r') as fh:
        return fh.read()


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PUB_KEY_PATH = os.path.join(TEST_DATA_DIR, "id_rsa.pub")
PUB_KEY = read_file(PUB_KEY_PATH)


def noop_sync(*args, **kwargs):
    pass


async def noop_async(*args, **kwargs):
    pass


@pytest.yield_fixture(scope='function')
def tmpdir():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


def die(*args, **kwargs):
    raise SigningScriptError("dying!")
