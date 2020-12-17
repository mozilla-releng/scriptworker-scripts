import json
from contextlib import asynccontextmanager
from copy import deepcopy
from unittest.mock import MagicMock

import pytest
from github3.exceptions import NotFoundError

import githubscript.github
from githubscript.script import main


@pytest.fixture
def config():
    return {
        "github_projects": {
            "fenix": {
                "allowed_actions": ["release"],
                "github_token": "SOME_TOKEN",
                "github_owner": "mozilla-mobile",
                "github_repo_name": "fenix",
                "contact_github": True,
            },
        },
        "taskcluster_scope_prefixes": ["project:mobile:fenix:releng:github:"],
        "verbose": True,
    }


@pytest.fixture
def task():
    return {
        "dependencies": ["dependency-task-id"],
        "scopes": ["project:mobile:fenix:releng:github:project:fenix", "project:mobile:fenix:releng:github:action:release"],
        "payload": {
            "artifactMap": [
                {
                    "paths": {
                        "public/build/arm64-v8a/geckoBeta/target.apk": {"destinations": ["firefox_preview_v5.2_arm64.apk"]},
                        "public/build/x86_64/geckoBeta/target.apk": {"destinations": ["firefox_preview_v5.2_x86_64.apk"]},
                    }
                }
            ],
            "gitTag": "v5.2.0",
            "gitRevision": "b94cfdf06be2be4b5a3c83ab4095eb2ecde7ba71",
            "isPrerelease": False,
            "releaseName": "Firefox 5.2",
            "upstreamArtifacts": [
                {
                    "paths": ["public/build/arm64-v8a/geckoBeta/target.apk", "public/build/x86_64/geckoBeta/target.apk"],
                    "taskId": "dependency-task-id",
                    "taskType": "signing",
                }
            ],
        },
    }


class _GitHubClient:
    _repository = MagicMock()

    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def repository(cls, *args, **kwargs):
        return cls._repository

    @classmethod
    def reset_repository(cls):
        cls._repository = MagicMock()
        return cls._repository


@pytest.fixture
def github3_repo_mock(monkeypatch):
    # _repository is a class attribute because githubscript instanciates it later and we
    # want to know get the value here. That's also why we reset it in this fixture.
    # It has to be reset from a test to another but not within a test.
    repo_mock = _GitHubClient.reset_repository()
    monkeypatch.setattr(githubscript.github, "GitHub", _GitHubClient)
    yield repo_mock


@asynccontextmanager
async def _RetryClientMock(*args, **kwargs):
    client_mock = MagicMock()

    @asynccontextmanager
    async def get_mock(*args, **kwargs):
        response_mock = MagicMock(status=200)
        yield response_mock

    client_mock.get = get_mock
    yield client_mock


@pytest.fixture
def retry_client_mock(monkeypatch):
    monkeypatch.setattr(githubscript.github, "RetryClient", _RetryClientMock)


@pytest.fixture
def valid_release_mock():
    valid_release_mock = MagicMock(
        tag_name="v5.2.0",
        target_commitish="release/v5.2.0",
        prerelease=False,
    )
    valid_release_mock.configure_mock(name="Firefox 5.2")

    yield valid_release_mock


@pytest.fixture
def valid_release_with_assets_mock(valid_release_mock):
    valid_release_with_assets_mock = deepcopy(valid_release_mock)
    first_asset_mock = MagicMock(content_type="application/vnd.android.package-archive", size=9)
    first_asset_mock.configure_mock(name="firefox_preview_v5.2_arm64.apk")
    second_asset_mock = MagicMock(content_type="application/vnd.android.package-archive", size=9)
    second_asset_mock.configure_mock(name="firefox_preview_v5.2_x86_64.apk")
    valid_release_with_assets_mock.assets.return_value = [first_asset_mock, second_asset_mock]

    yield valid_release_with_assets_mock


@pytest.fixture
def scriptworker_config(tmp_path, config, task):
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    config["work_dir"] = str(work_dir)

    config_path = tmp_path / "config.json"
    with open(config_path, "w") as config_file:
        json.dump(config, config_file)

    with open(work_dir / "task.json", "w") as task_file:
        json.dump(task, task_file)

    for arch in ("arm64-v8a", "x86_64"):
        dir = work_dir / "cot/dependency-task-id/public/build" / arch / "geckoBeta"
        dir.mkdir(parents=True)
        file_path = dir / "target.apk"
        with open(file_path, "wb") as f:
            f.write(b"some data")

    yield config_path


def test_main_create_release(github3_repo_mock, retry_client_mock, valid_release_mock, valid_release_with_assets_mock, scriptworker_config):
    github3_repo_mock.release_from_tag.side_effect = [
        NotFoundError(MagicMock()),
        valid_release_mock,
        valid_release_with_assets_mock,
    ]

    main(config_path=scriptworker_config)
    github3_repo_mock.create_release.assert_called_once_with(
        tag_name="v5.2.0", name="Firefox 5.2", draft=False, prerelease=False, target_commitish="b94cfdf06be2be4b5a3c83ab4095eb2ecde7ba71"
    )
    assert github3_repo_mock.edit.call_count == 0
    assert valid_release_mock.upload_asset.call_count == 2


def test_main_update_release(github3_repo_mock, retry_client_mock, valid_release_mock, valid_release_with_assets_mock, scriptworker_config):
    incomplete_release_mock = MagicMock(
        tag_name="v5.2.0",
        target_commitish="b94cfdf06be2be4b5a3c83ab4095eb2ecde7ba71",
        prerelease=False,
    )
    incomplete_release_mock.configure_mock(name="Firefox Preview 5.2")

    github3_repo_mock.release_from_tag.side_effect = [
        incomplete_release_mock,
        valid_release_mock,
        valid_release_with_assets_mock,
    ]

    main(config_path=scriptworker_config)
    assert github3_repo_mock.create_release.call_count == 0
    incomplete_release_mock.edit.assert_called_with(
        tag_name="v5.2.0",
        name="Firefox 5.2",
        draft=False,
        prerelease=False,
    )
    assert valid_release_mock.upload_asset.call_count == 2
