import os
import pytest
import tempfile

with open(os.path.join(os.path.dirname(__file__), "id_rsa.pub")) as fh:
    PUB_KEY = fh.read()


@pytest.yield_fixture(scope='function')
def tmpdir():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp
