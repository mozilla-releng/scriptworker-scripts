import base64
from pathlib import Path
from textwrap import dedent

import pytest
from simple_github.client import GITHUB_GRAPHQL_ENDPOINT
from yarl import URL


@pytest.mark.asyncio
async def test_commit(aioresponses, client):
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

    await client.commit(branch, message, additions, deletions)

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
                "branch": {"branchName": branch, "repositoryNameWithOwner": f"{client.owner}/{client.repo}"},
                "expectedHeadOid": head_oid,
                "fileChanges": {"additions": expected_additions, "deletions": expected_deletions},
                "message": {"headline": message},
            }
        },
    }


@pytest.mark.asyncio
async def test_get_files(aioresponses, client):
    branch = "main"
    expected = {"README.md": "Hello!", "version.txt": "109.1.0"}
    files = list(expected)

    aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=200, payload={"data": {"repository": {k: {"text": v} for k, v in expected.items()}}})

    result = await client.get_files(files, branch)
    assert result == expected

    aioresponses.assert_called()
    key = ("POST", URL(GITHUB_GRAPHQL_ENDPOINT))
    called_with = aioresponses.requests[key][-1][1]["json"]

    files = list(map(Path, files))
    assert called_with == {
        "query": dedent(
            f"""
            query getFileContents {{
              repository(owner: "{client.owner}", name: "{client.repo}") {{
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
