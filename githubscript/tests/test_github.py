from collections import namedtuple
from contextlib import asynccontextmanager
from contextlib import nullcontext as does_not_raise
from dataclasses import dataclass
from unittest.mock import MagicMock, mock_open, patch

import pytest
from github3.exceptions import NotFoundError
from scriptworker_client.exceptions import TaskError

import githubscript.github as github


@pytest.fixture
def release_config():
    return {
        "contact_github": True,
        "git_tag": "v1.0.0",
        "git_revision": "somecommithash",
        "github_owner": "some_owner",
        "github_repo_name": "some_repo",
        "github_token": "some_secret_token",
        "release_name": "SomeProduct v1.0.0",
        "is_prerelease": False,
    }


@dataclass
class _DummyRelease:
    tag_name: str = "v1.0.0"
    target_commitish: str = "some/gitbranch"
    name: str = "SomeProduct v1.0.0"
    prerelease: bool = False


@dataclass
class _DummyArtifact:
    content_type: str = "application/vnd.android.package-archive"
    browser_download_url: str = "https://some.url"
    name: str = "Target 1.apk"
    size: int = 9000


def _create_async_mock(monkeypatch_, target, max_calls=1):
    counter = (n for n in range(0, max_calls + 1))

    async def async_mock(*args, **kwargs):
        next(counter)

    monkeypatch_.setattr(github, target, async_mock)
    return counter


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "contact_github, release_exists, expected_init_calls, expected_update_calls, expected_create_calls, expected_upload_calls",
    ((False, False, 0, 0, 0, 0), (True, False, 1, 0, 1, 1), (True, True, 1, 1, 0, 1)),
)
async def test_release(
    monkeypatch, release_config, contact_github, release_exists, expected_init_calls, expected_update_calls, expected_create_calls, expected_upload_calls
):
    release_config["contact_github"] = contact_github
    init_call_counter = _create_async_mock(monkeypatch, "_init_github_client")
    _create_async_mock(monkeypatch, "_get_github_repository")

    get_release_call_counter = (n for n in range(0, 4))

    async def _mock_get_release(*args):
        if release_exists or next(get_release_call_counter) >= 1:
            return _DummyRelease()
        raise NotFoundError(MagicMock())

    monkeypatch.setattr(github, "_get_release_from_tag", _mock_get_release)

    update_call_counter = _create_async_mock(monkeypatch, "_update_release_if_needed")
    create_call_counter = _create_async_mock(monkeypatch, "_create_release")
    upload_call_counter = _create_async_mock(monkeypatch, "_upload_artifacts_if_needed")
    _create_async_mock(monkeypatch, "_check_final_state_of_release")

    await github.release(release_config)
    assert next(init_call_counter) == expected_init_calls
    assert next(update_call_counter) == expected_update_calls
    assert next(create_call_counter) == expected_create_calls
    assert next(upload_call_counter) == expected_upload_calls


@pytest.mark.asyncio
async def test_init_github_client(monkeypatch):
    github_client = MagicMock()
    monkeypatch.setattr(github, "GitHub", github_client)
    await github._init_github_client("some_secret_token")
    github_client.assert_called_once_with(token="some_secret_token")


@pytest.mark.asyncio
async def test_get_github_repository(release_config):
    github_client = MagicMock()
    await github._get_github_repository(github_client, release_config)
    github_client.repository.assert_called_once_with("some_owner", "some_repo")


@pytest.mark.asyncio
async def test_get_release_from_tag():
    github_repository = MagicMock()
    await github._get_release_from_tag(github_repository, "v1.0.0")
    github_repository.release_from_tag.assert_called_once_with("v1.0.0")


@pytest.mark.asyncio
async def test_create_release(release_config):
    github_repository = MagicMock()
    await github._create_release(github_repository, release_config)
    github_repository.create_release.assert_called_once_with(
        tag_name="v1.0.0",
        target_commitish="somecommithash",
        name="SomeProduct v1.0.0",
        draft=False,
        prerelease=False,
    )


@pytest.mark.asyncio
async def test_edit_existing_release(release_config):
    existing_release = MagicMock()
    await github._edit_existing_release(existing_release, release_config)
    existing_release.edit.assert_called_once_with(
        tag_name="v1.0.0",
        name="SomeProduct v1.0.0",
        draft=False,
        prerelease=False,
    )


@pytest.mark.asyncio
async def test_delete_artifact():
    existing_release = MagicMock()
    await github._delete_artifact(existing_release)
    existing_release.delete.assert_called_once_with()


@pytest.mark.asyncio
async def test_upload_artifact(tmpdir):
    existing_release = MagicMock()
    file_path = tmpdir.join("target.apk")
    artifact = {
        "content_type": "application/vnd.android.package-archive",
        "local_path": file_path,
        "name": "Target 1.apk",
    }

    mock_open_ = mock_open()
    # monkeypatch shouldn't be used to patch open()
    # https://docs.pytest.org/en/stable/monkeypatch.html#global-patch-example-preventing-requests-from-remote-operations
    with patch("githubscript.github.open", mock_open_):
        await github._upload_artifact(existing_release, artifact)

    mock_open_.assert_called_once_with(file_path, "rb")
    file_handle = mock_open_()

    existing_release.upload_asset.assert_called_once_with(
        content_type="application/vnd.android.package-archive",
        name="Target 1.apk",
        asset=file_handle,
    )


@pytest.mark.asyncio
async def test_get_contents():
    github_repository = MagicMock()
    await github._get_contents(github_repository, "path")
    github_repository.file_contents.assert_called_once_with("path", None)
    await github._get_contents(github_repository, "path", "refs/heads/main")
    github_repository.file_contents.assert_called_with("path", "refs/heads/main")


@pytest.mark.asyncio
async def test_get_branch():
    github_repository = MagicMock()
    await github._get_branch(github_repository, "main")
    github_repository.branch.assert_called_once_with("main")


@pytest.mark.parametrize(
    "include_target_commitish, expected_result",
    (
        (
            True,
            {
                "tag_name": "v1.0.0",
                "target_commitish": "somecommithash",
                "name": "SomeProduct v1.0.0",
                "draft": False,
                "prerelease": False,
            },
        ),
        (
            False,
            {
                "tag_name": "v1.0.0",
                "name": "SomeProduct v1.0.0",
                "draft": False,
                "prerelease": False,
            },
        ),
    ),
)
def test_get_github_release_kwargs(release_config, include_target_commitish, expected_result):
    assert github._get_github_release_kwargs(release_config, include_target_commitish) == expected_result


@pytest.mark.asyncio
@pytest.mark.parametrize("update_release, expected_edit_calls", ((False, 0), (True, 1)))
async def test_update_release_if_needed(monkeypatch, release_config, update_release, expected_edit_calls):
    existing_release = _DummyRelease()
    monkeypatch.setattr(github, "_does_release_need_to_be_updated", lambda *args: update_release)
    edit_call_counter = _create_async_mock(monkeypatch, "_edit_existing_release")

    await github._update_release_if_needed(existing_release, release_config)
    assert next(edit_call_counter) == expected_edit_calls


@pytest.mark.parametrize(
    "existing_release, expected_result",
    (
        (_DummyRelease(), False),
        (_DummyRelease(tag_name="v1.0.1"), True),
        (_DummyRelease(name="AnotherProduct v1.0.0"), True),
        (_DummyRelease(prerelease=True), True),
        # We don't want to update target_commitish otherwise it breaks CoT
        (_DummyRelease(target_commitish="somegithash"), False),
    ),
)
def test_does_release_need_to_be_updated(release_config, existing_release, expected_result):
    assert github._does_release_need_to_be_updated(existing_release, release_config) == expected_result


@pytest.mark.asyncio
async def test_upload_artifacts_if_needed(monkeypatch):
    existing_release = MagicMock()
    existing_release.assets.return_value = (_DummyArtifact(), _DummyArtifact(name="Target 2.apk"))
    release_config = {"artifacts": [{"name": "Target 1.apk"}, {"name": "Target 2.apk"}]}
    upload_call_counter = _create_async_mock(monkeypatch, "_upload_artifact_if_needed", max_calls=2)

    await github._upload_artifacts_if_needed(existing_release, release_config)
    assert next(upload_call_counter) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "artifact_exists, update_artifact, expected_delete_calls, expected_upload_calls",
    ((False, False, 0, 1), (False, True, 0, 1), (True, False, 0, 0), (True, True, 1, 1)),
)
async def test_upload_artifact_if_needed(monkeypatch, artifact_exists, update_artifact, expected_delete_calls, expected_upload_calls):
    existing_release = MagicMock()
    existing_artifacts = [_DummyArtifact()]
    artifact = {"name": "Target 1.apk"}

    def _dummy_get_artifact(*args):
        if artifact_exists:
            return _DummyArtifact()
        raise ValueError("")

    monkeypatch.setattr(github, "_get_existing_artifact", _dummy_get_artifact)

    async def _dummy_artifact_reupload(*args):
        return update_artifact

    monkeypatch.setattr(github, "_does_existing_artifact_need_to_be_reuploaded", _dummy_artifact_reupload)

    delete_call_counter = _create_async_mock(monkeypatch, "_delete_artifact")
    upload_call_counter = _create_async_mock(monkeypatch, "_upload_artifact")

    await github._upload_artifact_if_needed(existing_release, existing_artifacts, artifact)
    assert next(delete_call_counter) == expected_delete_calls
    assert next(upload_call_counter) == expected_upload_calls


@pytest.mark.parametrize(
    "existing_artifacts, target_artifact, expectation, expected_result",
    (
        (
            [_DummyArtifact()],
            {"name": "Target 1.apk"},
            does_not_raise(),
            _DummyArtifact(),
        ),
        (
            [_DummyArtifact(), _DummyArtifact(name="Target 2.apk")],
            {"name": "Target 2.apk"},
            does_not_raise(),
            _DummyArtifact(name="Target 2.apk"),
        ),
        (
            [_DummyArtifact()],
            {"name": "Target 2.apk"},
            pytest.raises(ValueError),
            None,
        ),
        (
            [_DummyArtifact(), _DummyArtifact()],
            {"name": "Target 1.apk"},
            pytest.raises(ValueError),
            None,
        ),
    ),
)
def test_get_existing_artifact(existing_artifacts, target_artifact, expectation, expected_result):
    with expectation:
        assert github._get_existing_artifact(existing_artifacts, target_artifact) == expected_result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "existing_artifact, target_artifact, artifact_exists, expected_result",
    (
        (
            _DummyArtifact(),
            {"content_type": "application/vnd.android.package-archive", "name": "Target 1.apk", "size": 9000},
            True,
            False,
        ),
        (
            _DummyArtifact("text/plain"),
            {"content_type": "application/vnd.android.package-archive", "name": "Target 1.apk", "size": 9000},
            True,
            True,
        ),
        (
            _DummyArtifact(size=1),
            {"content_type": "application/vnd.android.package-archive", "name": "Target 1.apk", "size": 9000},
            True,
            True,
        ),
        (
            _DummyArtifact(),
            {"content_type": "application/vnd.android.package-archive", "name": "Target 1.apk", "size": 9000},
            False,
            True,
        ),
    ),
)
async def test_does_existing_artifact_need_to_be_reuploaded(monkeypatch, existing_artifact, target_artifact, artifact_exists, expected_result):
    http_response = MagicMock()
    http_response.status = 200 if artifact_exists else 404

    @asynccontextmanager
    async def _dummy_http_get(*args, **kwargs):
        yield http_response

    @asynccontextmanager
    async def _dummy_http_client(*args, **kwargs):
        client_dummy = MagicMock()
        client_dummy.get = _dummy_http_get
        yield client_dummy

    monkeypatch.setattr(github, "RetryClient", _dummy_http_client)
    assert await github._does_existing_artifact_need_to_be_reuploaded(existing_artifact, target_artifact) == expected_result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "update_release, update_artifact, expectation",
    (
        (
            False,
            False,
            does_not_raise(),
        ),
        (
            True,
            False,
            pytest.raises(TaskError),
        ),
        (
            False,
            True,
            pytest.raises(TaskError),
        ),
    ),
)
async def test_check_final_state_of_release(monkeypatch, update_release, update_artifact, expectation):
    existing_release = MagicMock()
    existing_release.assets.return_value = []
    monkeypatch.setattr(github, "_does_release_need_to_be_updated", lambda *args: update_release)
    monkeypatch.setattr(github, "_get_existing_artifact", lambda *args: {})

    async def _dummy_artifact_reupload(*args, **kwargs):
        return update_artifact

    monkeypatch.setattr(github, "_does_existing_artifact_need_to_be_reuploaded", _dummy_artifact_reupload)

    release_config = {"artifacts": [{"name": "some_artifact"}]}
    with expectation:
        await github._check_final_state_of_release(existing_release, release_config)


def test_get_relevant_major_versions():
    repo = MagicMock()
    Release = namedtuple("Release", ["tag_name"])
    repo.releases.return_value = [Release("90.1.2"), Release("91.0.0")]
    assert github.get_relevant_major_versions(repo) == (90, 91)


def test_get_relevant_ac_branches():
    repo = MagicMock()
    Release = namedtuple("Release", ["tag_name"])
    repo.releases.return_value = [Release("90.1.2"), Release("91.0.0")]

    def get_branch(branch_name):
        if "90" in branch_name:
            raise NotFoundError(MagicMock())
        return True

    repo.branch.side_effect = get_branch
    assert list(github.get_relevant_ac_branches(repo)) == ["releases/91.0", "main"]
