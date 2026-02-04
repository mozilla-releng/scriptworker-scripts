import base64
import hashlib
from pathlib import Path
from string import Template
from textwrap import dedent

import pytest
from aioresponses import CallbackResult
from gql.transport.exceptions import TransportQueryError
from graphql import strip_ignored_characters
from simple_github.client import GITHUB_GRAPHQL_ENDPOINT
from yarl import URL

from scriptworker_client.github_client import UnknownBranchError


@pytest.mark.asyncio
async def test_create_branch(aioresponses, github_client):
    branch_name = "new-feature"
    from_branch = "main"
    repo_id = "R_abc123"
    source_oid = "def456"

    # First query gets repo ID and source OID
    aioresponses.post(
        GITHUB_GRAPHQL_ENDPOINT,
        status=200,
        payload={"data": {"repository": {"id": repo_id, "object": {"oid": source_oid}}}},
    )
    # Second query creates the branch
    aioresponses.post(
        GITHUB_GRAPHQL_ENDPOINT,
        status=200,
        payload={"data": {"createRef": {"ref": {"name": f"refs/heads/{branch_name}"}}}},
    )

    await github_client.create_branch(branch_name=branch_name, from_branch=from_branch)

    aioresponses.assert_called()
    key = ("POST", URL(GITHUB_GRAPHQL_ENDPOINT))
    info_request = aioresponses.requests[key][-2][1]["json"]
    create_request = aioresponses.requests[key][-1][1]["json"]

    assert info_request == {
        "query": dedent(
            f"""
            query getRepoInfo {{
              repository(owner: "{github_client.owner}", name: "{github_client.repo}") {{
                id
                object(expression: "{from_branch}") {{
                  oid
                }}
              }}
            }}"""
        ).strip(),
    }
    assert create_request == {
        "query": dedent(
            """
            mutation ($input: CreateRefInput!) {
              createRef(input: $input) {
                ref {
                  name
                }
              }
            }"""
        ).strip(),
        "variables": {
            "input": {
                "repositoryId": repo_id,
                "name": f"refs/heads/{branch_name}",
                "oid": source_oid,
            }
        },
    }


@pytest.mark.asyncio
async def test_create_branch_dry_run(aioresponses, github_client):
    branch_name = "new-feature"
    from_branch = "main"
    repo_id = "R_abc123"
    source_oid = "def456"

    # Only the info query should be made in dry_run mode
    aioresponses.post(
        GITHUB_GRAPHQL_ENDPOINT,
        status=200,
        payload={"data": {"repository": {"id": repo_id, "object": {"oid": source_oid}}}},
    )

    await github_client.create_branch(branch_name=branch_name, from_branch=from_branch, dry_run=True)

    aioresponses.assert_called()
    key = ("POST", URL(GITHUB_GRAPHQL_ENDPOINT))
    # Only one request should be made (the info query, not the mutation)
    assert len(aioresponses.requests[key]) == 1


@pytest.mark.asyncio
async def test_create_branch_unknown_source_branch(aioresponses, github_client):
    branch_name = "new-feature"
    from_branch = "nonexistent"

    aioresponses.post(
        GITHUB_GRAPHQL_ENDPOINT,
        status=200,
        payload={"data": {"repository": {"id": "R_abc123", "object": None}}},
    )

    with pytest.raises(UnknownBranchError, match=f"branch '{from_branch}' not found in repo!"):
        await github_client.create_branch(branch_name=branch_name, from_branch=from_branch)


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
    aliases = {
        "README.md": "a" + hashlib.md5("README.md".encode()).hexdigest(),
        "version.txt": "a" + hashlib.md5("version.txt".encode()).hexdigest(),
    }
    files = list(expected)

    aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=200, payload={"data": {"repository": {aliases[k]: {"text": v} for k, v in expected.items()}}})

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
                {aliases[str(files[0])]}: object(expression: "{branch}:{files[0]}") {{
                  ... on Blob {{
                    text
                  }}
                }}
                {aliases[str(files[1])]}: object(expression: "{branch}:{files[1]}") {{
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
async def test_get_files_multiple_requests(aioresponses, github_client):
    branch = "main"
    expected = {"README.md": "Hello!", "version.txt": "109.1.0"}
    aliases = {
        "README.md": "a" + hashlib.md5("README.md".encode()).hexdigest(),
        "version.txt": "a" + hashlib.md5("version.txt".encode()).hexdigest(),
    }
    files = list(expected)

    aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=200, payload={"data": {"repository": {aliases["README.md"]: {"text": expected["README.md"]}}}})
    aioresponses.post(GITHUB_GRAPHQL_ENDPOINT, status=200, payload={"data": {"repository": {aliases["version.txt"]: {"text": expected["version.txt"]}}}})

    result = await github_client.get_files(files, branch, files_per_request=1)
    assert result == expected

    aioresponses.assert_called()
    key = ("POST", URL(GITHUB_GRAPHQL_ENDPOINT))
    first_request = aioresponses.requests[key][-2][1]["json"]
    second_request = aioresponses.requests[key][-1][1]["json"]

    files = [Path(file) for file in files]
    assert first_request == {
        "query": dedent(
            f"""
            query getFileContents {{
              repository(owner: "{github_client.owner}", name: "{github_client.repo}") {{
                {aliases["README.md"]}: object(expression: "{branch}:README.md") {{
                  ... on Blob {{
                    text
                  }}
                }}
              }}
            }}
            """
        ).strip(),
    }
    assert second_request == {
        "query": dedent(
            f"""
            query getFileContents {{
              repository(owner: "{github_client.owner}", name: "{github_client.repo}") {{
                {aliases["version.txt"]}: object(expression: "{branch}:version.txt") {{
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
    aliases = {
        "README.md": "a" + hashlib.md5("README.md".encode()).hexdigest(),
        "version.txt": "a" + hashlib.md5("version.txt".encode()).hexdigest(),
        "missing.txt": "a" + hashlib.md5("missing.txt".encode()).hexdigest(),
    }

    aioresponses.post(
        GITHUB_GRAPHQL_ENDPOINT,
        status=200,
        payload={"data": {"repository": {aliases["README.md"]: {"text": "Hello!"}, aliases["version.txt"]: {"text": "109.1.0"}, aliases["missing.txt"]: None}}},
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
                {aliases[str(files[0])]}: object(expression: "{branch}:{files[0]}") {{
                  ... on Blob {{
                    text
                  }}
                }}
                {aliases[str(files[1])]}: object(expression: "{branch}:{files[1]}") {{
                  ... on Blob {{
                    text
                  }}
                }}
                {aliases[str(files[2])]}: object(expression: "{branch}:{files[2]}") {{
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


@pytest.mark.asyncio
async def test_get_repository_files(aioresponses, github_client):
    branch = "main"
    expected = [
        "file1",
        "file2",
        "a/b/bfile1",
        "a/b/c/d/e/deepfile1",
    ]

    # we expect more than one request because of the deeply nested file
    aioresponses.post(
        GITHUB_GRAPHQL_ENDPOINT,
        status=200,
        payload={
            "data": {
                "repository": {
                    "path0": {
                        "entries": [
                            {
                                "name": "file1",
                                "type": "blob",
                                "object": {},
                            },
                            {
                                "name": "file2",
                                "type": "blob",
                                "object": {},
                            },
                            {
                                "name": "a",
                                "type": "tree",
                                "object": {
                                    "entries": [
                                        {
                                            "name": "b",
                                            "type": "tree",
                                            "object": {
                                                "entries": [
                                                    {
                                                        "name": "bfile1",
                                                        "type": "blob",
                                                        "object": {},
                                                    },
                                                    {
                                                        "name": "c",
                                                        "type": "tree",
                                                        "object": {
                                                            "entries": [
                                                                {
                                                                    "name": "d",
                                                                    "type": "tree",
                                                                }
                                                            ]
                                                        },
                                                    },
                                                ],
                                            },
                                        },
                                    ]
                                },
                            },
                        ]
                    }
                }
            }
        },
    )
    aioresponses.post(
        GITHUB_GRAPHQL_ENDPOINT,
        status=200,
        payload={
            "data": {
                "repository": {
                    "path0": {"entries": [{"name": "e", "type": "tree", "object": {"entries": [{"name": "deepfile1", "type": "blob", "object": {}}]}}]}
                }
            }
        },
    )

    result = await github_client.get_file_listing(branch=branch, depth_per_query=4)
    assert result == expected

    aioresponses.assert_called()

    key = ("POST", URL(GITHUB_GRAPHQL_ENDPOINT))
    first_request = aioresponses.requests[key][-2][1]["json"]
    second_request = aioresponses.requests[key][-1][1]["json"]

    first_request["query"] = strip_ignored_characters(first_request["query"])
    assert first_request == {
        "query": Template(
            strip_ignored_characters(
                f"""
            query RepoFiles {{
              repository(owner: "$owner", name: "$repo") {{
                path0: object(expression: "main:") {{
                  ... on Tree {{
                    entries {{
                      name
                      type
                      object {{
                        ... on Tree {{
                          entries {{
                            name
                            type
                            object {{
                              ... on Tree {{
                                entries {{
                                  name
                                  type
                                  object {{
                                    ... on Tree {{
                                      entries {{
                                        name
                                        type
                                      }}
                                    }}
                                  }}
                                }}
                              }}
                            }}
                          }}
                        }}
                      }}
                    }}
                  }}
                }}
              }}
            }}
            """
            ),
        ).substitute(owner=github_client.owner, repo=github_client.repo)
    }
    second_request["query"] = strip_ignored_characters(second_request["query"])
    assert second_request == {
        "query": Template(
            strip_ignored_characters(
                f"""
            query RepoFiles {{
              repository(owner: "$owner", name: "$repo") {{
                path0: object(expression: "main:a/b/c/d") {{
                  ... on Tree {{
                    entries {{
                      name
                      type
                      object {{
                        ... on Tree {{
                          entries {{
                            name
                            type
                            object {{
                              ... on Tree {{
                                entries {{
                                  name
                                  type
                                  object {{
                                    ... on Tree {{
                                      entries {{
                                        name
                                        type
                                      }}
                                    }}
                                  }}
                                }}
                              }}
                            }}
                          }}
                        }}
                      }}
                    }}
                  }}
                }}
              }}
            }}
            """
            ),
        ).substitute(owner=github_client.owner, repo=github_client.repo)
    }


@pytest.mark.asyncio
async def test_get_file_listing_paths_per_query_inheritance(aioresponses, github_client):
    """Test that paths_per_query parameter is properly inherited in recursive calls."""
    branch = "main"
    paths = ["dir1", "dir2", "dir3", "dir4", "dir5"]  # More than paths_per_query=2, so we need to split

    # First call: processes first 2 paths (dir1, dir2)
    aioresponses.post(
        GITHUB_GRAPHQL_ENDPOINT,
        status=200,
        payload={
            "data": {
                "repository": {
                    "path0": {
                        "entries": [
                            {
                                "name": "file1.txt",
                                "type": "blob",
                            }
                        ]
                    },
                    "path1": {
                        "entries": [
                            {
                                "name": "file2.txt",
                                "type": "blob",
                            }
                        ]
                    },
                }
            }
        },
    )
    # Second call: processes excess paths with paths_per_query=2 (dir3, dir4)
    aioresponses.post(
        GITHUB_GRAPHQL_ENDPOINT,
        status=200,
        payload={
            "data": {
                "repository": {
                    "path0": {
                        "entries": [
                            {
                                "name": "file3.txt",
                                "type": "blob",
                            }
                        ]
                    },
                    "path1": {
                        "entries": [
                            {
                                "name": "file4.txt",
                                "type": "blob",
                            }
                        ]
                    },
                }
            }
        },
    )
    # Third call: processes remaining excess path (dir5) with paths_per_query=2
    aioresponses.post(
        GITHUB_GRAPHQL_ENDPOINT,
        status=200,
        payload={
            "data": {
                "repository": {
                    "path0": {
                        "entries": [
                            {
                                "name": "file5.txt",
                                "type": "blob",
                            }
                        ]
                    }
                }
            }
        },
    )

    result = await github_client.get_file_listing(paths=paths, branch=branch, paths_per_query=2)

    expected = ["dir1/file1.txt", "dir2/file2.txt", "dir3/file3.txt", "dir4/file4.txt", "dir5/file5.txt"]
    assert sorted(result) == sorted(expected)

    # Verify all 3 requests were made (this demonstrates paths_per_query is inherited)
    assert len(aioresponses.requests[("POST", URL(GITHUB_GRAPHQL_ENDPOINT))]) == 3


@pytest.mark.asyncio
async def test_get_repository_files_with_initial_subtree(aioresponses, github_client):
    branch = "main"
    expected = [
        "a/b/c/d/e/deepfile1",
    ]

    # we expect more than one request because of the deeply nested file
    aioresponses.post(
        GITHUB_GRAPHQL_ENDPOINT,
        status=200,
        payload={
            "data": {
                "repository": {
                    "path0": {
                        "entries": [
                            {
                                "name": "d",
                                "type": "tree",
                                "object": {
                                    "entries": [
                                        {
                                            "name": "e",
                                            "type": "tree",
                                        },
                                    ]
                                },
                            },
                        ]
                    }
                }
            }
        },
    )
    aioresponses.post(
        GITHUB_GRAPHQL_ENDPOINT,
        status=200,
        payload={
            "data": {
                "repository": {
                    "path0": {
                        "entries": [
                            {"name": "deepfile1", "type": "blob", "object": {}},
                        ]
                    }
                }
            }
        },
    )

    result = await github_client.get_file_listing("a/b/c", branch=branch, depth_per_query=2)
    assert result == expected

    aioresponses.assert_called()

    key = ("POST", URL(GITHUB_GRAPHQL_ENDPOINT))
    first_request = aioresponses.requests[key][-2][1]["json"]
    second_request = aioresponses.requests[key][-1][1]["json"]

    first_request["query"] = strip_ignored_characters(first_request["query"])

    assert first_request == {
        "query": Template(
            strip_ignored_characters(
                f"""
            query RepoFiles {{
              repository(owner: "$owner", name: "$repo") {{
                path0: object(expression: "main:a/b/c") {{
                  ... on Tree {{
                    entries {{
                      name
                      type
                      object {{
                        ... on Tree {{
                          entries {{
                            name
                            type
                          }}
                        }}
                      }}
                    }}
                  }}
                }}
              }}
            }}
            """
            ),
        ).substitute(owner=github_client.owner, repo=github_client.repo)
    }

    second_request["query"] = strip_ignored_characters(second_request["query"])
    assert second_request == {
        "query": Template(
            strip_ignored_characters(
                f"""
            query RepoFiles {{
              repository(owner: "$owner", name: "$repo") {{
                path0: object(expression: "main:a/b/c/d/e") {{
                  ... on Tree {{
                    entries {{
                      name
                      type
                      object {{
                        ... on Tree {{
                          entries {{
                            name
                            type
                          }}
                        }}
                      }}
                    }}
                  }}
                }}
              }}
            }}
            """
            ),
        ).substitute(owner=github_client.owner, repo=github_client.repo)
    }
