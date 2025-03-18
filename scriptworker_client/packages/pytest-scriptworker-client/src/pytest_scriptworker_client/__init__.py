from pathlib import Path

import pytest
import pytest_asyncio
from simple_github.client import GITHUB_API_ENDPOINT

from scriptworker_client.github_client import GithubClient

here = Path(__file__).parent


# TODO: move these to a re-usable location; see taskgraph for an example
@pytest.fixture(scope="session")
def datadir():
    return here / "data"


@pytest.fixture(scope="session")
def privkey_file(datadir):
    return datadir / "test_private_key.pem"


@pytest_asyncio.fixture
async def github_client(github_installation_responses, privkey_file):
    config = {"app_id": 12345, "privkey_file": privkey_file}
    owner = "mozilla-mobile"
    repo = "placeholder-repo"

    github_installation_responses(owner)

    client = GithubClient(config, owner, repo)
    yield client
    await client.close()


@pytest.fixture(scope="function")
def github_installation_responses(aioresponses):
    def inner(owner):
        aioresponses.get(
            f"{GITHUB_API_ENDPOINT}/app/installations",
            status=200,
            payload=[{"id": 1, "account": {"login": owner}}],
        )
        aioresponses.post(
            f"{GITHUB_API_ENDPOINT}/app/installations/1/access_tokens",
            status=200,
            payload={"token": "111"},
        )

    return inner
