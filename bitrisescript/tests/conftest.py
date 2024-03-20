import pytest
from aioresponses import aioresponses


@pytest.fixture
def responses():
    with aioresponses() as rsps:
        yield rsps


@pytest.fixture
def config():
    return {"bitrise": {"access_token": "abc"}, "taskcluster_scope_prefixes": ["test:prefix:"], "artifact_dir": "work/artifacts", "work_dir": "work"}
