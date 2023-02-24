import tempfile

import pytest

from scriptworker.context import Context

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
