from pathlib import Path
from textwrap import dedent

import pytest
from simple_github.client import GITHUB_GRAPHQL_ENDPOINT
from yarl import URL


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
