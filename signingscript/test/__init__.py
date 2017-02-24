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
