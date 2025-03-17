from pathlib import Path

import pytest
from scriptworker.context import Context

pytest_plugins = ("pytest-scriptworker-client",)

here = Path(__file__).parent


@pytest.fixture(scope="function")
def context(privkey_file, tmpdir):
    context = Context()
    context.config = {
        "artifact_dir": tmpdir,
        "lando_api": "https://lando.fake",
        "lando_name_to_github_repo": {
            "repo_name": {
                "owner": "faker",
                "repo": "fake_repo",
                "branch": "fake_branch",
            }
        },
        "github_config": {
            "app_id": 12345,
            "privkey_file": privkey_file,
        },
        "poll_time": 0,
        "sleeptime_callback": lambda _: 0,
    }
    return context


@pytest.fixture(scope="session")
def datadir():
    return here / "data"


@pytest.fixture(scope="session")
def privkey_file(datadir):
    return datadir / "test_private_key.pem"
