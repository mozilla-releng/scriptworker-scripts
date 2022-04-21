import os
from contextlib import nullcontext as does_not_raise
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from github3.exceptions import NotFoundError
from mozilla_version.maven import MavenVersion

from githubscript import application_services
from githubscript.constants import MAVEN

TEST_DATA_DIR = Path(os.path.dirname(__file__)) / "data"


def test_match_as_version():
    with open(TEST_DATA_DIR / "Dependencies.kt") as f:
        src = f.read()
    assert application_services.match_as_version(src) == "91.1.0"
    with pytest.raises(Exception):
        application_services.match_as_version("")


@pytest.mark.asyncio
async def test_get_current_as_version():
    github_repository = MagicMock()
    with open(TEST_DATA_DIR / "Dependencies.kt", "rb") as f:
        src = f.read()
    github_repository.file_contents.return_value.decoded = src
    assert await application_services.get_current_as_version(github_repository, "main") == "91.1.0"


@pytest.mark.parametrize(
    "major_version, version, expectation",
    (
        (91, "91.1.1", does_not_raise()),
        (94, None, pytest.raises(Exception)),
        (67, "67.2.0", does_not_raise()),
    ),
)
@patch("requests.get")
def test_get_latest_as_version(mock_get, major_version, version, expectation):
    with open(TEST_DATA_DIR / "appservices-metadata.xml") as f:
        mock_get.return_value.text = f.read()
    with expectation:
        assert application_services.get_latest_as_version(major_version) == version
    mock_get.assert_called_once_with(f"{MAVEN}/org/mozilla/appservices/nimbus/maven-metadata.xml")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "old, new, expectation",
    (
        # "old" doesn't match current
        ("old", "new", pytest.raises(Exception)),
        # old and new are the same
        ("91.1.0", "91.1.0", pytest.raises(Exception)),
        # actual upgrade
        ("91.1.0", "91.2.0", does_not_raise()),
    ),
)
async def test_update_as_version(old, new, expectation):
    repo = MagicMock()
    with open(TEST_DATA_DIR / "Dependencies.kt", "rb") as f:
        src = f.read()
    repo.file_contents.return_value.decoded = src
    with expectation:
        await application_services._update_as_version(repo, old, new, "main", "releng")


def mock_branch(branch_name):
    """Pretend the pr branch doesn't exist"""
    if branch_name == "releng/update-as/ac-main":
        raise NotFoundError(MagicMock())
    return MagicMock()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "current, latest, branch_exists, pr_created",
    (
        # no upgrade available
        ("91.2.0", "91.2.0", False, False),
        # upgrade available, but pr branch already exists
        ("91.1.0", "91.2.0", True, False),
        # upgrade available
        ("91.1.0", "91.2.0", False, True),
    ),
)
@patch("githubscript.application_services.get_latest_as_version")
@patch("githubscript.application_services.get_current_as_version")
async def test_update_application_services(get_current, get_latest, current, latest, branch_exists, pr_created):
    get_current.return_value = MavenVersion.parse(current)
    get_latest.return_value = MavenVersion.parse(latest)

    with open(TEST_DATA_DIR / "Dependencies.kt", "rb") as f:
        dependencies = f.read()
    ac_repo = MagicMock()
    if not branch_exists:
        ac_repo.branch.side_effect = mock_branch
    ac_repo.file_contents.return_value.decoded = dependencies
    await application_services.update_application_services(ac_repo, "main")
    if pr_created:
        ac_repo.create_pull.assert_called_once()
    else:
        ac_repo.create_pull.assert_not_called()
