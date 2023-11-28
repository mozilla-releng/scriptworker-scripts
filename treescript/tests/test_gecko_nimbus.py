import os
import subprocess

import pytest

import scriptworker_client.aio as aio
import treescript.gecko.nimbus as nimbus

from unittest.mock import AsyncMock


# build_commit_message {{{1
@pytest.mark.parametrize("dontbuild, ignore_closed_tree", ((True, True), (False, False)))
def test_build_commit_message(dontbuild, ignore_closed_tree):
    """build_commit_message adds the correct approval strings"""
    expected = "no bug - DESCRIPTION r=release a=nimbus"
    if dontbuild:
        expected += nimbus.DONTBUILD_MSG
    if ignore_closed_tree:
        expected += nimbus.CLOSED_TREE_MSG
    assert nimbus.build_commit_message("DESCRIPTION", dontbuild=dontbuild, ignore_closed_tree=ignore_closed_tree).rstrip() == expected


# android_nimbus_update {{{1
@pytest.mark.parametrize(
    "ignore_closed_tree, android_nimbus_update_info, old_contents, new_contents, changes",
    (
        (
            True,
            {"updates": [{"app_name": "fenix", "experiments_path": "app/src/experiments.json", "experiments_url": "https://example.com"}]},
            "existing experiment contents",
            "new experiment contents",
            1,
        ),
        (
            True,
            {"updates": [{"app_name": "fenix", "experiments_path": "app/src/experiments.json", "experiments_url": "https://example.com"}]},
            "existing experiment contents",
            "existing experiment contents",
            0,
        ),
        (
            False,
            {"updates": [{"app_name": "fenix", "experiments_path": "app/src/experiments.json", "experiments_url": "https://example.com"}]},
            "existing experiment contents",
            "new experiment contents",
            1,
        ),
    ),
)
@pytest.mark.asyncio
async def test_android_nimbus_update(mocker, ignore_closed_tree, android_nimbus_update_info, tmpdir, old_contents, new_contents, changes):
    """android_nimbus_update flow coverage."""

    async def check_treestatus(*args):
        return True

    open_mock = mocker.mock_open(read_data=old_contents)
    mocker.patch("builtins.open", open_mock, create=True)
    mocker.patch.object(os.path, "exists", return_value=True)

    mocker.patch.object(aio, "request")
    mocker.patch.object(subprocess, "run", return_value=subprocess.CompletedProcess(args=None, returncode=0, stdout=new_contents))
    mocker.patch.object(nimbus, "get_dontbuild", return_value=False)
    mocker.patch.object(nimbus, "get_ignore_closed_tree", return_value=ignore_closed_tree)
    mocker.patch.object(nimbus, "check_treestatus", new=check_treestatus)
    mocker.patch.object(nimbus, "get_android_nimbus_update_info", return_value=android_nimbus_update_info)
    mocker.patch.object(nimbus, "vcs", new=AsyncMock())

    assert await nimbus.android_nimbus_update({}, {}, tmpdir) == changes


@pytest.mark.asyncio
async def test_android_nimbus_update_closed_tree(mocker):
    """android_nimbus_update should exit if the tree is closed and ignore_closed_tree is
    False.

    """

    async def check_treestatus(*args):
        return False

    mocker.patch.object(aio, "request")
    mocker.patch.object(nimbus, "subprocess")
    mocker.patch.object(nimbus, "get_dontbuild", return_value=False)
    mocker.patch.object(nimbus, "get_ignore_closed_tree", return_value=False)
    mocker.patch.object(nimbus, "get_short_source_repo", return_value="mozilla-central")
    mocker.patch.object(nimbus, "check_treestatus", new=check_treestatus)
    # this will [intentionally] break if we fail to exit android_nimbus_update where
    # we're supposed to
    mocker.patch.object(nimbus, "get_android_nimbus_update_info", return_value={"from_repo_url": "x"})

    assert await nimbus.android_nimbus_update({}, {}, "") == 0
