import base64
import os
from pathlib import Path

import pytest
import pytest_asyncio
from simple_github.client import GITHUB_API_ENDPOINT

from treescript.gecko.mercurial import HGRCPATH
from treescript.github.client import GithubClient

ROBUSTCHECKOUT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "vendored", "robustcheckout.py"))
HGRC_ROBUSTCHECKOUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "robustcheckout.hgrc"))

here = Path(__file__).parent


@pytest.fixture(autouse=True)
def set_hgrc(monkeypatch):
    monkeypatch.setenv("HGRCPATH", os.path.pathsep.join([HGRCPATH, HGRC_ROBUSTCHECKOUT]))
    monkeypatch.setenv("ROBUSTCHECKOUT", ROBUSTCHECKOUT_PATH)


@pytest.fixture(scope="session")
def datadir():
    return here / "data"


@pytest.fixture(scope="session")
def privkey_file(datadir):
    return datadir / "test_private_key.pem"


@pytest.fixture(scope="session")
def pubkey(datadir):
    with open(datadir / "test_key.pub", "rb") as fh:
        return fh.read()


@pytest_asyncio.fixture
async def client(aioresponses, privkey_file):
    config = {"github_config": {"privkey_file": privkey_file}}
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
