from contextlib import nullcontext as does_not_raise

import pytest
from scriptworker_client.exceptions import TaskVerificationError

import githubscript.release_config as release_config


@pytest.mark.parametrize(
    "product_config, task_payload, expected_result",
    (
        (
            {
                "github_owner": "some_owner",
                "github_repo_name": "some_repo",
                "github_token": "some_secret_token",
                "contact_github": True,
            },
            {
                "gitRevision": "somecommithash",
                "gitTag": "v1.0.0",
                "isPrerelease": False,
                "releaseName": "SomeProduct v1.0.0",
            },
            {
                "artifacts": [
                    {
                        "content_type": "application/vnd.android.package-archive",
                        "local_path": "/dummy/path/to.apk",
                        "name": "somme_pretty_name.apk",
                        "size": 9000,
                    },
                ],
                "contact_github": True,
                "git_revision": "somecommithash",
                "git_tag": "v1.0.0",
                "github_owner": "some_owner",
                "github_repo_name": "some_repo",
                "github_token": "some_secret_token",
                "is_prerelease": False,
                "release_name": "SomeProduct v1.0.0",
            },
        ),
        (
            {
                "github_owner": "config_owner",
                "github_repo_name": "config_repo",
                "allow_github_repo_override": True,
                "github_token": "some_secret_token",
                "contact_github": True,
            },
            {
                "githubOwner": "task_owner",
                "githubRepoName": "task_repo",
                "gitRevision": "somecommithash",
                "gitTag": "v1.0.0",
                "isPrerelease": False,
                "releaseName": "SomeProduct v1.0.0",
            },
            {
                "artifacts": [
                    {
                        "content_type": "application/vnd.android.package-archive",
                        "local_path": "/dummy/path/to.apk",
                        "name": "somme_pretty_name.apk",
                        "size": 9000,
                    },
                ],
                "contact_github": True,
                "git_revision": "somecommithash",
                "git_tag": "v1.0.0",
                "github_owner": "task_owner",
                "github_repo_name": "task_repo",
                "github_token": "some_secret_token",
                "is_prerelease": False,
                "release_name": "SomeProduct v1.0.0",
            },
        ),
        (
            {
                "github_owner": "config_owner",
                "github_repo_name": "config_repo",
                "allow_github_repo_override": False,
                "github_token": "some_secret_token",
                "contact_github": True,
            },
            {
                "githubOwner": "task_owner",
                "githubRepoName": "task_repo",
                "gitRevision": "somecommithash",
                "gitTag": "v1.0.0",
                "isPrerelease": False,
                "releaseName": "SomeProduct v1.0.0",
            },
            {
                "artifacts": [
                    {
                        "content_type": "application/vnd.android.package-archive",
                        "local_path": "/dummy/path/to.apk",
                        "name": "somme_pretty_name.apk",
                        "size": 9000,
                    },
                ],
                "github_owner": "config_owner",
                "github_repo_name": "config_repo",
                "contact_github": True,
                "git_revision": "somecommithash",
                "git_tag": "v1.0.0",
                "github_token": "some_secret_token",
                "is_prerelease": False,
                "release_name": "SomeProduct v1.0.0",
            },
        ),
    ),
)
def test_release_config(monkeypatch, product_config, task_payload, expected_result):
    def _dummy_get_artifacts(*args, **kwargs):
        return [{"content_type": "application/vnd.android.package-archive", "local_path": "/dummy/path/to.apk", "name": "somme_pretty_name.apk", "size": 9000}]

    monkeypatch.setattr(release_config, "_get_artifacts", _dummy_get_artifacts)

    config = {}

    assert release_config.get_release_config(product_config, task_payload, config) == expected_result


@pytest.mark.parametrize(
    "product_config, task_payload",
    (
        (
            {
                "allow_github_repo_override": False,
                "github_token": "some_secret_token",
                "contact_github": True,
            },
            {
                "githubOwner": "some_owner",
                "githubRepoName": "some_repo",
                "gitRevision": "somecommithash",
                "gitTag": "v1.0.0",
                "isPrerelease": False,
                "releaseName": "SomeProduct v1.0.0",
            },
        ),
        (
            {
                "github_owner": "some_owner",
                "github_repo_name": "some_repo",
                "allow_github_repo_override": True,
                "github_token": "some_secret_token",
                "contact_github": True,
            },
            {
                "gitRevision": "somecommithash",
                "gitTag": "v1.0.0",
                "isPrerelease": False,
                "releaseName": "SomeProduct v1.0.0",
            },
        ),
    ),
)
def test_release_config_override_missing_key(monkeypatch, product_config, task_payload):
    def _dummy_get_artifacts(*args, **kwargs):
        return [{"content_type": "application/vnd.android.package-archive", "local_path": "/dummy/path/to.apk", "name": "somme_pretty_name.apk", "size": 9000}]

    monkeypatch.setattr(release_config, "_get_artifacts", _dummy_get_artifacts)

    config = {}

    with pytest.raises(TaskVerificationError):
        release_config.get_release_config(product_config, task_payload, config)


def test_get_artifacts(monkeypatch):
    config = {
        "work_dir": "/some/work/dir",
    }

    task_payload = {
        "artifactMap": "",
        "upstreamArtifacts": [
            {"paths": ["public/build/target.apk", "public/build/target2.apk"], "taskId": "someTaskId"},
            {"paths": ["public/build/target3.apk"], "taskId": "someOtherTaskId"},
        ],
    }

    def _dummy_find_target_path(taskcluster_path, _):
        if taskcluster_path.endswith("target.apk"):
            return "Target 1.apk"
        elif taskcluster_path.endswith("target2.apk"):
            return "Target 2.apk"
        elif taskcluster_path.endswith("target3.apk"):
            return "Target 3.apk"
        else:
            raise ValueError(f'Unsupported path "{taskcluster_path}"')

    monkeypatch.setattr(release_config, "_find_target_path", _dummy_find_target_path)
    monkeypatch.setattr("os.path.getsize", lambda _: 9000)

    assert release_config._get_artifacts(task_payload, config) == [
        {
            "content_type": "application/vnd.android.package-archive",
            "local_path": "/some/work/dir/cot/someTaskId/public/build/target.apk",
            "name": "Target 1.apk",
            "size": 9000,
        },
        {
            "content_type": "application/vnd.android.package-archive",
            "local_path": "/some/work/dir/cot/someTaskId/public/build/target2.apk",
            "name": "Target 2.apk",
            "size": 9000,
        },
        {
            "content_type": "application/vnd.android.package-archive",
            "local_path": "/some/work/dir/cot/someOtherTaskId/public/build/target3.apk",
            "name": "Target 3.apk",
            "size": 9000,
        },
    ]


@pytest.mark.parametrize(
    "taskcluster_path, artifact_map, expectation, expected_result",
    (
        (
            "public/build/target.apk",
            [{"paths": {"public/build/target.apk": {"destinations": ["Target 1.apk"]}}}],
            does_not_raise(),
            "Target 1.apk",
        ),
        (
            "public/build/target.apk",
            [
                {"paths": {"public/build/target2.apk": {"destinations": ["Target 2.apk"]}}},
                {"paths": {"public/build/target.apk": {"destinations": ["Target 1.apk"]}}},
            ],
            does_not_raise(),
            "Target 1.apk",
        ),
        (
            "public/build/target.apk",
            [{"paths": {"public/build/target.apk": {"destinations": []}}}],
            pytest.raises(TaskVerificationError),
            None,
        ),
        (
            "public/build/target.apk",
            [{"paths": {"public/build/target.apk": {"destinations": ["Target 1.apk", "Another target 1.apk"]}}}],
            pytest.raises(TaskVerificationError),
            None,
        ),
        (
            "public/build/target.apk",
            [
                {"paths": {"public/build/target.apk": {"destinations": ["Target 1.apk"]}}},
                {"paths": {"public/build/target.apk": {"destinations": ["Another target 1.apk"]}}},
            ],
            pytest.raises(TaskVerificationError),
            None,
        ),
        (
            "public/build/target.apk",
            [],
            pytest.raises(TaskVerificationError),
            None,
        ),
    ),
)
def test_find_target_path(taskcluster_path, artifact_map, expectation, expected_result):
    with expectation:
        assert release_config._find_target_path(taskcluster_path, artifact_map) == expected_result
