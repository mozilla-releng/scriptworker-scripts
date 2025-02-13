import pytest

from scriptworker.context import Context


@pytest.fixture(scope="function")
def context(tmpdir):
    context = Context()
    context.config = {}
    return context
