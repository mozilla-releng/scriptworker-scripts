#!/usr/bin/env python
"""Treescript branch methods."""

from typing import Dict

from scriptworker_client.github_client import GithubClient

from treescript.util.task import get_branch, get_create_branch_info, should_push


def get_branch_name(task: Dict) -> str:
    """Get the source branch name from a task's create_branch_info.

    Args:
        task (Dict): The task definition containing create_branch_info.

    Returns:
        str: The name of the branch to create from, or None if not specified.
    """
    create_branch_info = get_create_branch_info(task)
    return create_branch_info.get("branch_name")


async def create_branch(client: GithubClient, task: Dict) -> None:
    """Create a new branch in the repository based on task configuration.

    Args:
        client (GithubClient): GithubClient instance for associated repo.
        task (Dict): The task definition containing branch configuration.
    """
    await client.create_branch(
        branch_name=get_branch_name(task),
        from_branch=get_branch(task),
        dry_run=not should_push(task),
    )
