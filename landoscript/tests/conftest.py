from pathlib import Path
from yarl import URL

import pytest
from scriptworker.context import Context
from simple_github.client import GITHUB_GRAPHQL_ENDPOINT

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
        "treestatus_url": "https://treestatus.fake",
    }
    return context


@pytest.fixture(scope="session")
def datadir():
    return here / "data"


@pytest.fixture(scope="session")
def privkey_file(datadir):
    return datadir / "test_private_key.pem"


def setup_test(github_installation_responses, context, payload, actions, repo="repo_name"):
    lando_repo = payload["lando_repo"]
    lando_api = context.config["lando_api"]
    owner = context.config["lando_name_to_github_repo"][lando_repo]["owner"]
    submit_uri = URL(f"{lando_api}/api/v1/{lando_repo}")
    job_id = 12345
    status_uri = URL(f"{lando_api}/push/{job_id}")

    github_installation_responses(owner)

    scopes = [f"project:releng:lando:repo:{repo}"]
    for action in actions:
        scopes.append(f"project:releng:lando:action:{action}")

    return submit_uri, status_uri, job_id, scopes


def setup_fetch_files_response(aioresponses, code, initial_values={}):
    if initial_values:
        github_response = {}
        for file, contents in initial_values.items():
            github_response[file] = f"{contents}"

        payload = {
            "data": {
                "repository": {k: {"text": v} for k, v in github_response.items()},
            }
        }
    else:
        payload = {}

    aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=code, payload=payload)


def assert_lando_submission_response(requests, submit_uri, attempts=1):
    assert ("POST", submit_uri) in requests
    reqs = requests[("POST", submit_uri)]
    assert len(reqs) == attempts
    # there might be more than one in cases where we retry; we assume that
    # the requests are the same for all attempts
    return reqs[0]


def assert_status_response(requests, status_uri, attempts=1):
    assert ("GET", status_uri) in requests
    reqs = requests[("GET", status_uri)]
    # there might be more than one in cases where we retry; we assume that
    # the requests are the same for all attempts
    assert len(reqs) == attempts
