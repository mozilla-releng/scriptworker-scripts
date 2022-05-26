import tempfile

import pytest


@pytest.fixture(scope="function")
def tmpdir():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp
