import os
from unittest.mock import AsyncMock

import pytest

from treescript.github import versionmanip as vmanip
from treescript.script import get_default_config


@pytest.fixture(scope="function")
def config(tmpdir):
    config_ = get_default_config()
    config_["work_dir"] = os.path.join(tmpdir, "work")
    yield config_


@pytest.fixture()
def mobile_repo_context(tmpdir, config, request, mocker):
    context = mocker.MagicMock()
    context.repo = os.path.join(tmpdir, "repo")
    context.task = {"metadata": {"source": "https://github.com/mozilla-mobile/firefox-android/blob/rev/foo"}}
    context.config = config
    os.mkdir(context.repo)
    version_file = os.path.join(context.repo, "version.txt")
    with open(version_file, "w") as f:
        f.write("109.0")
    yield context


@pytest.mark.asyncio
async def test_bump_version_mobile(mocker, mobile_repo_context):
    bump_info = {"files": ["version.txt"], "next_version": "110.1.0"}
    mocked_bump_info = mocker.patch.object(vmanip, "get_version_bump_info")
    mocked_bump_info.return_value = bump_info
    vcs_mock = AsyncMock()
    mocker.patch.object(vmanip, "vcs", new=vcs_mock)
    await vmanip.bump_version(mobile_repo_context.config, mobile_repo_context.task, mobile_repo_context.repo)
