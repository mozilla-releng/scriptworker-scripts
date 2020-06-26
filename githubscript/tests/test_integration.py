import json
from contextlib import asynccontextmanager
from copy import deepcopy
from unittest.mock import MagicMock

import pytest

import githubscript.github
from githubscript.script import main


@pytest.fixture
def config():
    return {
        "github_projects": {
            "fenix": {"allowed_actions": ["release"], "github_token": "SOME_TOKEN", "github_owner": "mozilla-mobile", "github_repo_name": "fenix"}
        },
        "taskcluster_scope_prefixes": ["project:mobile:fenix:releng:github:"],
        "verbose": True,
        "contact_github": True,
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
            "releaseName": "Firefox Preview 5.2",
            "releaseDescription": "Thanks for trying out Firefox Preview! In 5.2, we have lots of new improvements.",
            "upstreamArtifacts": [
                {
                    "paths": ["public/build/arm64-v8a/geckoBeta/target.apk", "public/build/x86_64/geckoBeta/target.apk"],
                    "taskId": "dependency-task-id",
                    "taskType": "signing",
                }
            ],
        },
    }


def test_main_update_release(monkeypatch, tmp_path, config, task):
    github3_mock = MagicMock()
    monkeypatch.setattr(githubscript.github, "github3", github3_mock)

    github_client_mock = MagicMock()
    github3_mock.GitHub.return_value = github_client_mock
    github_repository_mock = MagicMock()
    github_client_mock.repository.return_value = github_repository_mock

    incomplete_release_mock = MagicMock(tag_name="v5.2.0", target_commitish="b94cfdf06be2be4b5a3c83ab4095eb2ecde7ba71", prerelease=False,)
    incomplete_release_mock.configure_mock(name="Firefox Preview 5.2")

    valid_release_mock = deepcopy(incomplete_release_mock)
    valid_release_mock = MagicMock(
        tag_name="v5.2.0",
        target_commitish="b94cfdf06be2be4b5a3c83ab4095eb2ecde7ba71",
        body="Thanks for trying out Firefox Preview! In 5.2, we have lots of new improvements.",
        prerelease=False,
    )
    valid_release_mock.configure_mock(name="Firefox Preview 5.2")

    valid_release_with_assets_mock = deepcopy(valid_release_mock)
    first_asset_mock = MagicMock(content_type="application/vnd.android.package-archive", size=9)
    first_asset_mock.configure_mock(name="firefox_preview_v5.2_arm64.apk")
    second_asset_mock = MagicMock(content_type="application/vnd.android.package-archive", size=9)
    second_asset_mock.configure_mock(name="firefox_preview_v5.2_x86_64.apk")
    valid_release_with_assets_mock.assets.return_value = [first_asset_mock, second_asset_mock]

    github_repository_mock.release_from_tag.side_effect = [
        incomplete_release_mock,
        valid_release_mock,
        valid_release_with_assets_mock,
    ]

    @asynccontextmanager
    async def RetryClientMock(*args, **kwargs):
        client_mock = MagicMock()

        @asynccontextmanager
        async def get_mock(*args, **kwargs):
            response_mock = MagicMock(status=200)
            yield response_mock

        client_mock.get = get_mock
        yield client_mock

    monkeypatch.setattr(githubscript.github, "RetryClient", RetryClientMock)

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

    main(config_path=config_path)
    incomplete_release_mock.edit.assert_called_with(
        tag_name="v5.2.0",
        target_commitish="b94cfdf06be2be4b5a3c83ab4095eb2ecde7ba71",
        name="Firefox Preview 5.2",
        body="Thanks for trying out Firefox Preview! In 5.2, we have lots of new improvements.",
        draft=False,
        prerelease=False,
    )
    assert valid_release_mock.upload_asset.call_count == 2
