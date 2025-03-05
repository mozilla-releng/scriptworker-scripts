"""Treescript git functions."""

import logging
import typing
from string import Template
from textwrap import dedent
from typing import Dict, List, Optional, TypedDict, Union

from simple_github import AppClient, AsyncClient

log = logging.getLogger(__name__)


class UnknownBranchError(Exception):
    pass


AppId = int
Owner = str
Repo = str


class GithubConfig(TypedDict):
    privkey_file: str
    app_id: AppId


class GithubClient:
    def __init__(self, github_config: GithubConfig, owner: Owner, repo: Repo):
        with open(github_config["privkey_file"]) as fh:
            privkey = fh.read()
        self.app_id = github_config["app_id"]
        self.owner = owner
        self.repo = repo
        self._client = typing.cast(AsyncClient, AppClient(self.app_id, privkey, owner=owner, repositories=[repo]))

    async def close(self):
        await self._client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *excinfo):
        await self.close()

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
        sentinel_slash = "__slash__"
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
            name = f.replace(".", sentinel_dot).replace("/", sentinel_slash)
            fields.append(field.substitute(branch=branch, file=f, name=name))

        query = query.substitute(owner=self.owner, repo=self.repo, fields=",".join(fields))

        contents = (await self._client.execute(query))["repository"]
        return {k.replace(sentinel_dot, ".").replace(sentinel_slash, "/"): v["text"] for k, v in contents.items()}
