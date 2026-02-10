#!/usr/bin/env python
"""Tests for treescript github branch methods."""

import pytest

import treescript.github.branch as branch
from treescript.exceptions import TreeScriptError


def test_get_branch_name():
    task = {
        "payload": {
            "create_branch_info": {
                "branch_name": "release-v1.0",
            }
        }
    }
    assert branch.get_branch_name(task) == "release-v1.0"


def test_get_branch_name_not_specified():
    task = {
        "payload": {
            "create_branch_info": {
                "from_branch": "main",
            }
        }
    }
    with pytest.raises(TreeScriptError):
        branch.get_branch_name(task)


@pytest.mark.asyncio
async def test_create_branch(mocker, github_client):
    task = {
        "payload": {
            "branch": "main",
            "create_branch_info": {
                "branch_name": "release-v1.0",
            },
        }
    }

    mock_create_branch = mocker.patch.object(github_client, "create_branch")

    await branch.create_branch(github_client, task)

    mock_create_branch.assert_called_once_with(
        branch_name="release-v1.0",
        from_branch="main",
        dry_run=False,
    )


@pytest.mark.asyncio
async def test_create_branch_dry_run(mocker, github_client):
    task = {
        "payload": {
            "branch": "main",
            "create_branch_info": {
                "branch_name": "release-v1.0",
            },
            "dry_run": True,
        }
    }

    mock_create_branch = mocker.patch.object(github_client, "create_branch")

    await branch.create_branch(github_client, task)

    mock_create_branch.assert_called_once_with(
        branch_name="release-v1.0",
        from_branch="main",
        dry_run=True,
    )
