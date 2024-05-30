"""Treescript git functions."""

import base64
import logging
from collections import defaultdict
from string import Template
from textwrap import dedent
from typing import Dict, List, Optional, Union

from gql.transport.exceptions import TransportQueryError
from simple_github import AppClient

from scriptworker_client.utils import retry_async

log = logging.getLogger(__name__)


class GithubClient:
    def __init__(self, config, owner, repo):
        with open(config["github_config"]["privkey_file"]) as fh:
            privkey = fh.read()
        self.app_id = config["github_config"]["app_id"]
        self.owner = owner
        self.repo = repo
        self._client = AppClient(self.app_id, privkey, owner=owner, repositories=[repo])

    async def close(self):
        await self._client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *excinfo):
        await self.close()

    async def commit(self, branch: str, message: str, additions: Optional[Dict[str, str]] = None, deletions: Optional[List[str]] = None) -> None:
        """Commit changes to the given repository and branch.

        Args:
            branch (str): The branch name to commit to.
            message (str): The commit message to use.
            additions (Dict): Files to add or update in the commit. Of the form
                `{<path>: <contents>}` (optional).
            deletions (List): Files to delete in the commit. Of the form
                `[<path>]` (optional).
        """
        changes = defaultdict(list)
        if additions:
            for name, contents in additions.items():
                changes["additions"].append({"path": name, "contents": base64.b64encode(contents.encode("utf-8")).decode("utf-8")})

        if deletions:
            changes["deletions"] = [{"path": p} for p in deletions]

        if not changes:
            log.warn("No changes to commit, aborting.")
            return

        oid_query = Template(
            """
            query getLatestCommit {
              repository(owner: "$owner", name: "$repo") {
                object(expression: "$branch") {
                  oid
                }
              }
            }
            """
        )
        oid_query = oid_query.substitute(owner=self.owner, repo=self.repo, branch=branch)

        commit_query = """
            mutation ($input: CreateCommitOnBranchInput!) {
              createCommitOnBranch(input: $input)  {
                commit { url }
              }
            }
        """
        variables = {
            "input": {
                "branch": {
                    "repositoryNameWithOwner": f"{self.owner}/{self.repo}",
                    "branchName": branch,
                },
                "message": {"headline": message},
                "fileChanges": changes,
                "expectedHeadOid": None,
            }
        }

        # Retry the query a few times in-case the head_oid was changed.
        async def _execute():
            head_oid = (await self._client.execute(oid_query))["repository"]["object"]["oid"]
            variables["input"]["expectedHeadOid"] = head_oid
            await self._client.execute(commit_query, variables=variables)

        await retry_async(_execute, attempts=3, retry_exceptions=(TransportQueryError,), sleeptime_kwargs={"delay_factor": 0})

    async def get_files(self, files: Union[str, List[str]], branch: Optional[str] = None) -> Dict[str, str]:
        """Get the contents of the specified files.

        Args:
            files (List): The list of files to retrieve.
            branch (str): The branch to retrieve the files from. Uses the
                repository's default branch if unspecified.

        Returns:
            Dict: The dictionary of file contents of the form `{<path>: <contents>}`.
        """
        branch = branch or "HEAD"

        if isinstance(files, str):
            files = [files]

        # Periods are not legal GraphQL key names.
        sentinel_dot = "__dot__"
        query = Template(
            dedent(
                """
            query getFileContents {
              repository(owner: "$owner", name: "$repo") {
                  $fields
              }
            }
            """
            )
        )
        field = Template(
            dedent(
                """
            $name: object(expression: "$branch:$file") {
              ... on Blob {
                text
              }
            }
            """
            )
        )
        fields = []
        for f in files:
            fields.append(field.substitute(branch=branch, file=f, name=f.replace(".", sentinel_dot)))

        query = query.substitute(owner=self.owner, repo=self.repo, fields=",".join(fields))

        contents = (await self._client.execute(query))["repository"]
        return {k.replace(sentinel_dot, "."): v["text"] for k, v in contents.items()}
