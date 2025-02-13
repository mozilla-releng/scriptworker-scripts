from pathlib import Path

import pytest
import pytest_asyncio
from scriptworker.context import Context
from simple_github.client import GITHUB_API_ENDPOINT

from landoscript.github import GithubClient, GithubConfig

here = Path(__file__).parent


@pytest.fixture(scope="function")
def context(privkey_file):
    context = Context()
    context.config = {
        "lando_api": "https://lando.fake",
        "github_config": {
            "app_id": 12345,
            "privkey_file": privkey_file,
        },
    }
    return context


@pytest.fixture(scope="session")
def datadir():
    return here / "data"


@pytest.fixture(scope="session")
def privkey_file(datadir):
    return datadir / "test_private_key.pem"


@pytest_asyncio.fixture
async def github_client(aioresponses, privkey_file):
    config: GithubConfig = {"app_id": 12345, "privkey_file": privkey_file}
    owner = "mozilla-mobile"
    repo = "placeholder-repo"
    inst_id = 1

    aioresponses.get(
        f"{GITHUB_API_ENDPOINT}/app/installations",
        status=200,
        payload=[{"id": inst_id, "account": {"login": owner}}],
    )
    aioresponses.post(
        f"{GITHUB_API_ENDPOINT}/app/installations/{inst_id}/access_tokens",
        status=200,
        payload={"token": "111"},
    )

    client = GithubClient(config, owner, repo)
    yield client
    await client.close()
