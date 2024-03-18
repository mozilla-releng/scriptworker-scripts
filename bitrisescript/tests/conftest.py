import pytest
from aioresponses import aioresponses


@pytest.fixture
def responses():
    with aioresponses() as rsps:
        yield rsps


@pytest.fixture
def config():
    return {"bitrise": {"token": "abc"}, "taskcluster_scope_prefixes": ["test:prefix:"], "work_dir": "work"}
