"""Treescript git functions."""

import base64
import hashlib
import logging
from collections import defaultdict
from pathlib import Path
from string import Template
from textwrap import dedent
from typing import Any, Dict, List, Optional, Tuple, Union

from gql.transport.exceptions import TransportQueryError
from simple_github import AppClient

from scriptworker_client.utils import retry_async

log = logging.getLogger(__name__)


class UnknownBranchError(Exception):
    pass


class EmptyPathError(Exception):
    pass


class GithubClient:
    def __init__(self, github_config, owner, repo):
        with open(github_config["privkey_file"]) as fh:
            privkey = fh.read()
        self.app_id = github_config["app_id"]
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
            head_oid = await self.get_branch_head_oid(branch)
            variables["input"]["expectedHeadOid"] = head_oid
            await self._client.execute(commit_query, variables=variables)

        await retry_async(_execute, attempts=3, retry_exceptions=(TransportQueryError,), sleeptime_kwargs={"delay_factor": 0})

    async def get_files(self, files: Union[str, List[str]], branch: Optional[str] = None, files_per_request: int = 200, mode: Optional[str] = None) -> Dict[str, Union[str, Dict[str, Optional[str]]]]:
        """Get the contents of the specified files.

        Args:
            files (List): The list of files to retrieve.
            branch (str): The branch to retrieve the files from. Uses the
                repository's default branch if unspecified.
            files_per_request (int): The number of files to request per GraphQL
                call. When fetching larger files, this number may need to be
                decreased to avoid timeouts. Defaults to 200.

        Returns:
            Dict: The dictionary of file contents of the form `{<path>: <contents>}`.
        """
        branch = branch or "HEAD"

        if isinstance(files, str):
            files = [files]

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
              ... on Tree {
              entries {
                    name
                    mode
                    object {
                        ... on Blob {
                            text
                        }
                    }
                }
            }
        }
            """
            )
        )
        # Many characters (slashes, dashes, dots, and more) are not supported
        # in graphql key names. Additionally, key names have a maximum length
        # of 320 characters. To avoid running afoul of these things, we map
        # file paths to their hashes, and use the hashes as the key names
        # in the query.
        aliases = {}
        ret: Dict[str, Union[str, Dict[str, Optional[str]]]] = {}

        # yields the starting index for each batch
        for i in range(0, len(files), files_per_request):
            fields = []
            # iterate over only the files in the current batch
            for f in files[i : i + files_per_request]:
                # Graphql assumes that any string that starts with a digit is an
                # integer, which will cause errors when the query is submitted.
                # We force these hashes to start with a letter to avoid hitting
                # this.
                hash_ = "a" + hashlib.md5(f.encode()).hexdigest()
                aliases[hash_] = f
                fields.append(field.substitute(branch=branch, file=f, name=hash_))

            str_query = query.substitute(owner=self.owner, repo=self.repo, fields=",".join(fields))

            contents = (await self._client.execute(str_query))["repository"]
            for k, v in contents.items():
                # Map the key names (which are the hashes we set-up above) back
                # to their actual file paths.
                name = aliases[k]
                if v is None:
                    ret[name] = None
                else: 
                    if mode:
                        ret[name] = {"mode": v.get("mode"), "text": v.get("text")}
                    else:
                        ret[name] = v.get("text")

        return ret

    async def get_branch_head_oid(self, branch: str) -> str:
        """Get the revision of the tip of the given branch.
        Args:
            branch (str): The branch to find the revision for.

        Returns: The revision of the tip of the given branch.
        """

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
        str_oid_query = oid_query.substitute(owner=self.owner, repo=self.repo, branch=branch)

        repo = (await self._client.execute(str_oid_query))["repository"]
        if "object" not in repo:
            raise UnknownBranchError(f"branch '{branch}' not found in repo!")

        return repo["object"]["oid"]

    async def get_file_listing(self, paths: Union[str, List[str]] = "", branch: Optional[str] = None, depth_per_query=5, paths_per_query=1) -> List[str]:
        """Get the recursive file and directory listings of the given path on
        the given branch, `depth_per_query` levels deep at a time.

        Args:
            paths (str or List[str]): The path, relative to the root of the repository, to
                fetch file listings for. Fetches the listings for the entire
                repository if not given.
            branch (str): The branch to find file listings for. If not given,
                `HEAD` is used.
            depth_per_query (int): The number of directories deep to query
                with each request to the GraphQL API. Repositories containing
                very large numbers of files or directories will need to use
                lower `depth_per_query` values to avoid timeouts.
            paths_per_query (int): The maximum number of paths included
                in a single GraphQL request. Lower values reduce the risk of
                timeouts when querying repositories with a very large number of
                files or directories , but higher values will decrease the number
                of total GraphQL queries issued.
        """

        branch = branch or "HEAD"

        if isinstance(paths, list) and not len(paths):
            raise EmptyPathError("Empty path lists are not supported.")

        if isinstance(paths, str):
            paths = [paths]

        excess_paths = []
        if len(paths) > paths_per_query:
            excess_paths = paths[paths_per_query:]
            paths = paths[:paths_per_query]

        leaf_expr = dedent(
            """
                    ... on Tree {
                      entries {
                        name
                        type
                      }
                    }
                    """
        )
        recursive_expr = Template(
            dedent(
                """
                    ... on Tree {
                      entries {
                        name
                        type
                        object {
                          $obj_expr
                        }
                      }
                    }
                    """
            )
        )
        file_expr = leaf_expr
        for _ in range(depth_per_query - 1):
            file_expr = recursive_expr.substitute(obj_expr=file_expr)

        # Use aliases here because `path` may contain characters not allowed in keys.
        # This ensures we avoid invalid identifiers and makes lookups safe.
        object_queries = []
        for i, path in enumerate(paths):
            alias = f"path{i}"
            object_queries.append(f'{alias}: object(expression: "{branch}:{path}") {{ {file_expr} }}')

        query = Template(
            dedent(
                """
            query RepoFiles {
              repository(owner: "$owner", name: "$repo") {
                $objects
              }
            }
                """
            )
        )

        str_query = query.substitute(owner=self.owner, repo=self.repo, objects="\n".join(object_queries))

        # Fetch all of the file listings in `path` up to `depth_per_query`
        resp = await self._client.execute(str_query)

        # Process the returing entries
        # Any subtrees that were not fully traversed will be returned in `refetches`
        # We need to refetch data starting at each of these subtrees to ensure we
        # don't miss anything.

        files = []
        refetches = excess_paths
        repo_data = resp["repository"]
        for i, path in enumerate(paths):
            alias = f"path{i}"
            node = repo_data.get(alias)
            if not node:
                continue
            entries = node.get("entries")
            files_, refetches_ = self._process_file_listings(entries, prefix=Path(path))
            refetches.extend([str(reftch) for reftch in refetches_])
            files.extend(files_)

        if refetches:
            refetch_files = await self.get_file_listing(refetches, branch, depth_per_query, paths_per_query)
            files.extend(refetch_files)

        return files

    def _process_file_listings(self, entries: List[Dict[str, Any]], prefix: Path = Path("")) -> Tuple[List[str], List[Path]]:
        """Process the `entries` from a response from a `get_file_listings` query.

        Args:
            entries (List): A list of entries returned from `get_file_listings` query.
            prefix (Path): A prefix to apply to each entry. This should be the same as
                the `path` given to `get_file_listings` in order to ensure paths are correct.

        Returns: A tuple of `files` and `refetches`. Files are a list of all `blob` entries
            found. Refetches are a list of all `tree` entries found that whose contents
            were not in the `entries` given. Both of these lists returned paths relative to
            `prefix`.
        """

        files = []
        refetches = []
        for entry in entries:
            name = prefix / entry["name"]
            if entry["type"] == "blob":
                # blobs are just files, easy!
                files.append(str(name))
            elif entry["type"] == "tree":
                # trees are directories.
                if "object" in entry:
                    # if there's an `object` in the entry it means we've fetched the
                    # directory contents; we just need to pull out its files & refetches
                    files_, refetches_ = self._process_file_listings(entry["object"].get("entries", []), name)
                    files.extend(files_)
                    refetches.extend(refetches_)
                else:
                    # if there's no `object` in the entry it means this directory
                    # was deep enough in the query that its contents were not fetched
                    # if the caller wants them, it will need to requery for them.
                    refetches.append(name)

        return files, refetches
