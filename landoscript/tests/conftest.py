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

    scopes = [f"project:releng:landoscript:repo:{repo}"]
    for action in actions:
        scopes.append(f"project:releng:landoscript:action:{action}")

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
    # TODO: improve this...now that we're doing retries we could have multiple requests.
    # how do make sure that more than one happened only if there was an error?
    # make sure that exactly one request was made
    # (a single request can add multiple actions, so there should never
    # be a need for more than 1 request)
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


def assert_add_commit_response(action, commit_msg_strings, initial_values, expected_bumps):
    # ensure metadata is correct
    assert action["author"] == "Release Engineering Landoscript <release+landoscript@mozilla.com>"
    # we don't actually verify the value here; it's not worth the trouble of mocking
    assert "date" in action

    # ensure required substrings are in the diff header
    for msg in commit_msg_strings:
        assert msg in action["commitmsg"]

    diffs = action["diff"].split("diff\n")

    # ensure expected bumps are present to a reasonable degree of certainty
    for file, after in expected_bumps.items():
        for diff in diffs:
            # if the version is the last line in the file it may or may not
            # have a trailing newline. either way, there will be one (and
            # only one) in the `-` line of the diff. account for this.
            # the `after` version will only have a newline if the file is
            # intended to have one after the diff has been applied.
            before = initial_values[file].rstrip("\n") + "\n"
            if file in diff and f"\n-{before}+{after}" in diff:
                break
        else:
            assert False, f"no version bump found for {file}: {diffs}"
