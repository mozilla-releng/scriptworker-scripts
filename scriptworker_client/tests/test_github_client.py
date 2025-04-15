import base64
from pathlib import Path
from textwrap import dedent

import pytest
from aioresponses import CallbackResult
from gql.transport.exceptions import TransportQueryError
from simple_github.client import GITHUB_GRAPHQL_ENDPOINT
from yarl import URL

from scriptworker_client.github_client import UnknownBranchError


@pytest.mark.asyncio
async def test_commit(aioresponses, github_client):
    branch = "main"
    message = "Commit it!"
    additions = {"version.txt": "foobar"}
    deletions = [
        "README.md",
    ]
    head_oid = "123"

    # First query is to get the oid of last commit
    aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=200, payload={"data": {"repository": {"object": {"oid": head_oid}}}})
    # Second query is to commit
    aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=200, payload={"data": {}})

    await github_client.commit(branch, message, additions, deletions)

    aioresponses.assert_called()
    key = ("POST", URL(GITHUB_GRAPHQL_ENDPOINT))
    called_with = aioresponses.requests[key][-1][1]["json"]

    expected_additions = [{"path": k, "contents": base64.b64encode(v.encode("utf-8")).decode("utf-8")} for k, v in additions.items()]
    expected_deletions = [{"path": d} for d in deletions]
    assert called_with == {
        "query": dedent(
            """
            mutation ($input: CreateCommitOnBranchInput!) {
              createCommitOnBranch(input: $input) {
                commit {
                  url
                }
              }
            }
            """
        ).strip(),
        "variables": {
            "input": {
                "branch": {"branchName": branch, "repositoryNameWithOwner": f"{github_client.owner}/{github_client.repo}"},
                "expectedHeadOid": head_oid,
                "fileChanges": {"additions": expected_additions, "deletions": expected_deletions},
                "message": {"headline": message},
            }
        },
    }


@pytest.mark.asyncio
async def test_commit_retry(aioresponses, github_client):
    head_oid = "123"
    branch = "main"
    message = "Commit it!"
    additions = {"version.txt": "foobar"}
    expected_attempts = 3

    counter = 0

    def callback(url, **kwargs):
        nonlocal counter
        counter += 1
        if counter % 2 == 1:
            return CallbackResult(status=200, payload={"data": {"repository": {"object": {"oid": head_oid}}}})
        return CallbackResult(
            status=200,
            payload={
                "errors": [
                    {
                        "type": "NOT_FOUND",
                        "path": ["createCommitOnBranch"],
                        "locations": [{"line": 2, "column": 3}],
                        "message": f"No commit exists with specified expectedHeadOid '{head_oid}'.",
                    }
                ]
            },
        )

    aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, callback=callback, repeat=True)

    with pytest.raises(TransportQueryError):
        await github_client.commit(branch, message, additions)

    assert counter == expected_attempts * 2  # two queries per attempt


@pytest.mark.asyncio
async def test_get_files(aioresponses, github_client):
    branch = "main"
    expected = {"README.md": "Hello!", "version.txt": "109.1.0"}
    files = list(expected)

    aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=200, payload={"data": {"repository": {k: {"text": v} for k, v in expected.items()}}})

    result = await github_client.get_files(files, branch)
    assert result == expected

    aioresponses.assert_called()
    key = ("POST", URL(GITHUB_GRAPHQL_ENDPOINT))
    called_with = aioresponses.requests[key][-1][1]["json"]

    files = list(map(Path, files))
    assert called_with == {
        "query": dedent(
            f"""
            query getFileContents {{
              repository(owner: "{github_client.owner}", name: "{github_client.repo}") {{
                {files[0].stem}__dot__{files[0].suffix[1:]}: object(expression: "{branch}:{files[0]}") {{
                  ... on Blob {{
                    text
                  }}
                }}
                {files[1].stem}__dot__{files[1].suffix[1:]}: object(expression: "{branch}:{files[1]}") {{
                  ... on Blob {{
                    text
                  }}
                }}
              }}
            }}
            """
        ).strip(),
    }


@pytest.mark.asyncio
async def test_get_files_with_missing(aioresponses, github_client):
    branch = "main"
    files = ["README.md", "version.txt", "missing.txt"]
    expected = {"README.md": "Hello!", "version.txt": "109.1.0", "missing.txt": None}

    aioresponses.post(
        GITHUB_GRAPHQL_ENDPOINT,
        status=200,
        payload={"data": {"repository": {"README.md": {"text": "Hello!"}, "version.txt": {"text": "109.1.0"}, "missing.txt": None}}},
    )

    result = await github_client.get_files(files, branch)
    assert result == expected

    aioresponses.assert_called()
    key = ("POST", URL(GITHUB_GRAPHQL_ENDPOINT))
    called_with = aioresponses.requests[key][-1][1]["json"]

    files = list(map(Path, files))
    assert called_with == {
        "query": dedent(
            f"""
            query getFileContents {{
              repository(owner: "{github_client.owner}", name: "{github_client.repo}") {{
                {files[0].stem}__dot__{files[0].suffix[1:]}: object(expression: "{branch}:{files[0]}") {{
                  ... on Blob {{
                    text
                  }}
                }}
                {files[1].stem}__dot__{files[1].suffix[1:]}: object(expression: "{branch}:{files[1]}") {{
                  ... on Blob {{
                    text
                  }}
                }}
                {files[2].stem}__dot__{files[2].suffix[1:]}: object(expression: "{branch}:{files[2]}") {{
                  ... on Blob {{
                    text
                  }}
                }}
              }}
            }}
            """
        ).strip(),
    }


@pytest.mark.asyncio
async def test_get_branch_head_oid(aioresponses, github_client):
    branch = "main"
    head_oid = "123"

    aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=200, payload={"data": {"repository": {"object": {"oid": head_oid}}}})

    result = await github_client.get_branch_head_oid(branch)
    assert result == head_oid

    aioresponses.assert_called()
    key = ("POST", URL(GITHUB_GRAPHQL_ENDPOINT))
    called_with = aioresponses.requests[key][-1][1]["json"]

    assert called_with == {
        "query": dedent(
            f"""
            query getLatestCommit {{
              repository(owner: "{github_client.owner}", name: "{github_client.repo}") {{
                object(expression: "{branch}") {{
                  oid
                }}
              }}
            }}
            """
        ).strip(),
    }


@pytest.mark.asyncio
async def test_get_branch_head_oid_branch_not_found(aioresponses, github_client):
    aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=200, payload={"data": {"repository": {"ref": None}}})

    with pytest.raises(UnknownBranchError, match="branch 'branchy' not found in repo!"):
        await github_client.get_branch_head_oid("branchy")
