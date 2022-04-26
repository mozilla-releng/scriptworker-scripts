import json
import os
from contextlib import nullcontext as does_not_raise
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

import pytest
from mozilla_version.maven import MavenVersion

import githubscript.geckoview as geckoview
from githubscript.constants import MAVEN

TEST_DATA_DIR = Path(os.path.dirname(__file__)) / "data"

with open(TEST_DATA_DIR / "Gecko.kt") as f:
    GECKO_KT = f.read()
with open(TEST_DATA_DIR / "Dependencies.kt") as f:
    DEPENDENCIES_KT = f.read()
with open(TEST_DATA_DIR / "geckoview.module") as f:
    GECKOVIEW_MODULE = f.read()


@pytest.mark.parametrize(
    "channel, expectation",
    (
        ("nightly", does_not_raise()),
        ("beta", does_not_raise()),
        ("release", does_not_raise()),
        ("esr", pytest.raises(Exception)),
        ("NIGHTLY", pytest.raises(Exception)),
    ),
)
def test_validate_gv_channel(channel, expectation):
    with expectation:
        assert geckoview.validate_gv_channel(channel) == channel


def test_match_gv_version():
    assert geckoview.match_gv_version(GECKO_KT) == "90.0.20210420095122"
    with pytest.raises(Exception):
        geckoview.match_gv_version("")


def test_match_gv_channel():
    assert geckoview.match_gv_channel(GECKO_KT) == "nightly"
    with pytest.raises(Exception):
        geckoview.match_gv_channel("")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "major_version, channel, version, expectation, path",
    (
        (90, "nightly", "90.1.2", does_not_raise(), "geckoview-nightly-omni"),
        (95, "beta", "95.0.20220414", does_not_raise(), "geckoview-beta-omni"),
        (99, "release", "99.0.20220227094054", does_not_raise(), "geckoview-omni"),
        (98, "release", None, pytest.raises(Exception), "geckoview-omni"),
    ),
)
@patch("aiohttp_retry.client.RetryClient.get")
async def test_get_latest_gv_version(mock_get, major_version, channel, version, expectation, path):
    mock_get.return_value.__aenter__.return_value.text.return_value = (
        "<metadata><versioning><versions>"
        "<version>90.1.2</version>"
        "<version>95.0.20220414</version>"
        "<version>99.0.20220227094054</version>"
        "</versions></versioning></metadata>"
    )

    with expectation:
        assert version == await geckoview.get_latest_gv_version(major_version, channel)
    mock_get.assert_any_call(f"{MAVEN}/org/mozilla/geckoview/{path}/maven-metadata.xml")


@pytest.mark.asyncio
async def test_get_current_gv_channel_and_version():
    github_repository = MagicMock()
    github_repository.file_contents.return_value.decoded = GECKO_KT.encode("ascii")
    channel, version = await geckoview.get_current_gv_channel_and_version(github_repository, "main")
    assert (channel, version) == ("nightly", "90.0.20210420095122")


@pytest.mark.asyncio
@patch("aiohttp_retry.client.RetryClient.get")
async def test_get_latest_glean_version(mock_get):
    mock_get.return_value.__aenter__.return_value.text.return_value = GECKOVIEW_MODULE
    assert await geckoview.get_latest_glean_version("95.0.20211218203254", "release") == "42.1.0"
    mock_get.assert_called_once_with(f"{MAVEN}/org/mozilla/geckoview/geckoview-omni/95.0.20211218203254/geckoview-omni-95.0.20211218203254.module")
    mock_get.reset_mock()
    assert await geckoview.get_latest_glean_version("95.0.20211218203254", "beta") == "42.1.0"
    mock_get.assert_called_once_with(f"{MAVEN}/org/mozilla/geckoview/geckoview-beta-omni/95.0.20211218203254/geckoview-beta-omni-95.0.20211218203254.module")
    module_bogus = json.loads(GECKOVIEW_MODULE)
    module_bogus["variants"][0]["capabilities"].append({"version": "44.0.0", "name": "glean-native", "group": "org.mozilla.telemetry"})
    mock_get.return_value.__aenter__.return_value.text.return_value = json.dumps(module_bogus)
    mock_get.reset_mock()
    with pytest.raises(Exception):
        await geckoview.get_latest_glean_version("95.0.20211218203254", "beta")
    mock_get.assert_called_once_with(f"{MAVEN}/org/mozilla/geckoview/geckoview-beta-omni/95.0.20211218203254/geckoview-beta-omni-95.0.20211218203254.module")


@pytest.mark.asyncio
async def test_get_current_glean_version():
    github_repository = MagicMock()
    github_repository.file_contents.return_value.decoded = DEPENDENCIES_KT.encode("ascii")
    assert await geckoview.get_current_glean_version(github_repository, "main") == "44.0.0"

    github_repository.file_contents.return_value.decoded = b""
    with pytest.raises(Exception):
        await geckoview.get_current_glean_version(github_repository, "main")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "old_version, new_version, expectation",
    (
        # ok
        ("44.0.0", "44.1.0", does_not_raise()),
        # old_version is not the current version
        ("41.1.0", "45.0.0", pytest.raises(Exception)),
    ),
)
async def test_update_glean_version(old_version, new_version, expectation):
    ac_repo = MagicMock()
    ac_repo.file_contents.return_value.decoded = DEPENDENCIES_KT.encode("ascii")
    with expectation:
        await geckoview._update_glean_version(ac_repo, old_version, new_version, "main", "githubscript")
        ac_repo.file_contents.return_value.update.assert_called_once_with("Update Glean to 44.1.0.", ANY, branch="main", author="githubscript")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "old_version, new_version, expectation",
    (
        # ok
        ("90.0.20210420095122", "90.0.20220419151600", does_not_raise()),
        # old_version is not the current version
        ("90.0.20210320095122", "90.0.20210420095122", pytest.raises(Exception)),
        # old_version and new_version are the same
        ("90.0.20210420095122", "90.0.20210420095122", pytest.raises(Exception)),
    ),
)
async def test_update_gv_version(old_version, new_version, expectation):
    ac_repo = MagicMock()
    ac_repo.file_contents.return_value.decoded = GECKO_KT.encode("ascii")
    with expectation:
        await geckoview._update_gv_version(ac_repo, old_version, new_version, "main", "nightly", "githubscript")
        ac_repo.file_contents.return_value.update.assert_called_once_with(
            f"Update GeckoView (Nightly) to {new_version}.", ANY, branch="main", author="githubscript"
        )


@pytest.mark.asyncio
@patch("githubscript.geckoview._update_ac_buildconfig")
@patch("githubscript.geckoview.get_current_version")
@patch("githubscript.geckoview.get_latest_glean_version")
@patch("githubscript.geckoview.get_current_glean_version")
@patch("githubscript.geckoview.get_latest_gv_version")
@patch("githubscript.geckoview.get_current_gv_channel_and_version")
async def test_update_geckoview(
    get_gv_channel_and_version,
    get_latest_gv_version,
    get_current_glean_version,
    get_latest_glean_version,
    get_current_version,
    update_ac_buildconfig,
):
    # update GV and Glean versions: create one PR
    get_gv_channel_and_version.return_value = "nightly", MavenVersion.parse("90.0.20210420095122")
    get_latest_gv_version.return_value = MavenVersion.parse("90.0.20220419151600")
    get_current_glean_version.return_value = MavenVersion.parse("44.0.0")
    get_latest_glean_version.return_value = MavenVersion.parse("44.1.0")
    get_current_version.return_value = MavenVersion.parse("90.0.18")
    ac_repo = MagicMock()
    ac_repo.branch.side_effect = [geckoview.NotFoundError(MagicMock()), MagicMock()]  # first call for pr_branch, second for release branch
    await geckoview._update_geckoview(ac_repo, "main")
    ac_repo.create_pull.assert_called_once()

    ac_repo.create_pull.reset_mock()

    # update GV, not glean: one PR
    get_gv_channel_and_version.return_value = "nightly", MavenVersion.parse("90.0.20210420095122")
    get_latest_gv_version.return_value = MavenVersion.parse("90.0.20220419151600")
    get_current_glean_version.return_value = MavenVersion.parse("44.0.0")
    get_latest_glean_version.return_value = MavenVersion.parse("44.0.0")
    ac_repo.branch.side_effect = [geckoview.NotFoundError(MagicMock()), MagicMock()]  # first call for pr_branch, second for release branch
    await geckoview._update_geckoview(ac_repo, "main")
    ac_repo.create_pull.assert_called_once()

    ac_repo.create_pull.reset_mock()

    # update GV on release branch: one PR, and version bump
    get_gv_channel_and_version.return_value = "beta", MavenVersion.parse("90.0.20210420095122")
    get_latest_gv_version.return_value = MavenVersion.parse("90.0.20220419151600")
    get_current_glean_version.return_value = MavenVersion.parse("44.0.0")
    get_latest_glean_version.return_value = MavenVersion.parse("44.0.0")
    ac_repo.branch.side_effect = [geckoview.NotFoundError(MagicMock()), MagicMock()]  # first call for pr_branch, second for release branch
    await geckoview._update_geckoview(ac_repo, "releases_v90.0")
    ac_repo.create_pull.assert_called_once()

    ac_repo.create_pull.reset_mock()

    # no newer version: no PR created
    get_latest_gv_version.return_value = MavenVersion.parse("90.0.20210420095122")
    ac_repo.branch.side_effect = [geckoview.NotFoundError(MagicMock()), MagicMock()]  # first call for pr_branch, second for release branch
    await geckoview._update_geckoview(ac_repo, "main")
    ac_repo.create_pull.assert_not_called()

    ac_repo.create_pull.reset_mock()

    # PR branch exists: no PR created
    get_latest_gv_version.return_value = MavenVersion.parse("90.0.20220419151600")
    ac_repo.branch.side_effect = [MagicMock()]
    await geckoview._update_geckoview(ac_repo, "main")
    ac_repo.create_pull.assert_not_called()


@pytest.mark.asyncio
@patch("githubscript.github._init_github_client")
async def test_bump_geckoview_no_contact_github(gh_init):
    bump_config = {"contact_github": False}
    await geckoview.bump_geckoview(bump_config)
    gh_init.assert_not_called()


@pytest.mark.asyncio
@patch("githubscript.github.get_relevant_ac_branches")
@patch("githubscript.application_services.update_application_services")
@patch("githubscript.geckoview._update_geckoview")
@patch("githubscript.github._get_github_repository")
@patch("githubscript.github._init_github_client")
async def test_bump_geckoview_main(gh_init, get_gh_repo, update_gv, update_as, get_branches):
    bump_config = {
        "contact_github": True,
        "github_token": "dummy",
        "github_owner": "mozilla-releng",
        "github_repo_name": "staging-android-components",
    }
    get_branches.return_value = ["main"]
    await geckoview.bump_geckoview(bump_config)
    gh_init.assert_called_once_with("dummy")
    update_gv.assert_called_once()
    update_as.assert_called_once()


@pytest.mark.asyncio
@patch("githubscript.github.get_relevant_ac_branches")
@patch("githubscript.application_services.update_application_services")
@patch("githubscript.geckoview._update_geckoview")
@patch("githubscript.github._get_github_repository")
@patch("githubscript.github._init_github_client")
async def test_bump_geckoview_release(gh_init, get_gh_repo, update_gv, update_as, get_branches):
    bump_config = {
        "contact_github": True,
        "github_token": "dummy",
        "github_owner": "mozilla-releng",
        "github_repo_name": "staging-android-components",
    }
    get_branches.return_value = ["releases_v100"]
    await geckoview.bump_geckoview(bump_config)
    gh_init.assert_called_once_with("dummy")
    update_gv.assert_called_once()
    update_as.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "old_version, new_version, expectation",
    (
        ("90.0.2", "90.1.3", does_not_raise()),
        ("100.100.0", "101.0.1", does_not_raise()),
        ("100.100.0", "100.100.0", pytest.raises(Exception)),
    ),
)
async def test_update_ac_version(old_version, new_version, expectation):
    ac_repo = MagicMock()
    ac_repo.file_contents.return_value.decoded = f"{old_version}\n".encode("ascii")
    with expectation:
        await geckoview._update_ac_version(ac_repo, old_version, new_version, "main", "githubscript")
        ac_repo.file_contents.return_value.update.assert_called_once_with(
            f"Set version to {new_version}.", f"{new_version}\n".encode("ascii"), branch="main", author="githubscript"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "old_version, new_version, expectation",
    (
        ("90.0.2", "90.1.3", does_not_raise()),
        ("100.100.0", "101.0.1", does_not_raise()),
        ("100.100.0", "100.100.0", pytest.raises(Exception)),
    ),
)
async def test_update_ac_buildconfig(old_version, new_version, expectation):
    ac_repo = MagicMock()
    with open(TEST_DATA_DIR / "buildconfig.yml", "rb") as f:
        ac_repo.file_contents.return_value.decoded = f.read().replace(b"{version}", old_version.encode("ascii"))
    with expectation:
        await geckoview._update_ac_buildconfig(ac_repo, old_version, new_version, "main", "githubscript")
        ac_repo.file_contents.return_value.update.assert_called_once_with(f"Set version to {new_version}.", ANY, branch="main", author="githubscript")
