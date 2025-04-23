import base64

import pytest
from simple_github.client import GITHUB_GRAPHQL_ENDPOINT
from mozilla_version.ios import MobileIosVersion
from yarl import URL
from pytest_scriptworker_client import get_files_payload

from treescript.github import versionmanip as vmanip
from treescript.exceptions import TreeScriptError
from contextlib import nullcontext as does_not_raise


@pytest.mark.asyncio
async def test_bump_version_mobile(aioresponses, github_client):
    head_rev = "abcdef"
    next_version = "110.1.0"
    task = {
        "payload": {
            "push": True,
            "version_bump_info": {
                "files": ["version.txt"],
                "next_version": next_version,
            },
        },
        "metadata": {
            "source": f"https://github.com/foo/bar/blob/{head_rev}/taskcluster/ci/version-bump",
        },
    }

    # First query is to get the contents of 'version.txt'
    aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=200, payload=get_files_payload({"version.txt": "109.1.0"}))
    # Second query is to get the head_rev
    aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=200, payload={"data": {"repository": {"object": {"oid": head_rev}}}})
    # Third query is to commit
    aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=200, payload={"data": {}})

    await vmanip.bump_version(github_client, task)

    aioresponses.assert_called()
    key = ("POST", URL(GITHUB_GRAPHQL_ENDPOINT))
    called_with = aioresponses.requests[key][-1]

    changes = called_with[1]["json"]["variables"]["input"]["fileChanges"]
    assert "deletions" not in changes
    assert len(changes["additions"]) == 1

    change = changes["additions"][0]
    assert change["path"] == "version.txt"
    assert base64.b64decode(change["contents"]).decode("utf-8") == next_version


@pytest.mark.parametrize(
    "file, source_repo, expectation, expected_result",
    (
        ("version.txt", "https://github.com/mozilla-mobile/firefox-ios", does_not_raise(), MobileIosVersion),
        ("version.txt", "https://github.com/mozilla-mobile/staging-firefox-ios", does_not_raise(), MobileIosVersion),
        ("version.txt", "https://github.com/mozilla-mobile/firefox-android", pytest.raises(TreeScriptError), None),
    ),
)
def test_find_what_version_parser_to_use(file, source_repo, expectation, expected_result):
    with expectation:
        assert vmanip._find_what_version_parser_to_use(file, source_repo) == expected_result
