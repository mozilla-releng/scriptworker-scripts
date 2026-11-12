import inspect
import os

import pytest
from scriptworker_client.client import verify_task_schema
from scriptworker_client.exceptions import TaskVerificationError

from treescript.util import task as ttask
from treescript.script import get_default_config

@pytest.fixture(scope="function")
def task_defn():
    return {
        "provisionerId": "meh",
        "workerType": "workertype",
        "schedulerId": "task-graph-scheduler",
        "taskGroupId": "some",
        "routes": [],
        "retries": 5,
        "created": "2015-05-08T16:15:58.903Z",
        "deadline": "2015-05-08T18:15:59.010Z",
        "expires": "2016-05-08T18:15:59.010Z",
        "dependencies": ["VALID_TASK_ID"],
        "scopes": ["project:mobile:firefox-ios:treescript:action:version_bump"],
        "payload": {
            "upstreamArtifacts": [
                {"taskType": "build", "taskId": "VALID_TASK_ID", "formats": ["gpg"], "paths": ["public/build/firefox-52.0a1.en-US.win64.installer.exe"]}
            ]
        },
        "metadata": {"source": "https://github.com/mozilla-mobile/firefox-ios/blob/1b4ab9a276ce7bb217c02b83057586e7946860f9/taskcluster/ci/foobar"},
    }


@pytest.fixture(scope="function")
def config(tmpdir):
    config_ = get_default_config()
    config_["work_dir"] = os.path.join(tmpdir, "work")
    config_["trust_domain"] = "mobile"
    yield config_


# verify_task_schema {{{1
def test_missing_mandatory_urls_are_reported(config, task_defn):
    del task_defn["scopes"]

    with pytest.raises(TaskVerificationError):
        verify_task_schema(config, task_defn)


def test_no_error_is_reported_when_no_missing_url(config, task_defn):
    verify_task_schema(config, task_defn)


@pytest.mark.parametrize(
    "source_url,raises",
    (
        ("https://bitbucket.org/mozilla/mozilla-central/file/foobar", TaskVerificationError),
        ("https://hg.mozilla.org/releases/mozilla-test-source/file/default/taskcluster/ci/foobar", TaskVerificationError),
        ("http://github.com/mozilla-mobile/firefox-ios/blob/default/taskcluster/ci/foobar", TaskVerificationError),
        ("https://github.com/mozilla-mobile/firefox-ios/raw/default/taskcluster/ci/foobar", TaskVerificationError),
    ),
)
def test_get_source_repo_raises(task_defn, source_url, raises):
    task_defn["metadata"]["source"] = source_url
    with pytest.raises(raises):
        ttask.get_source_repo(task_defn)


@pytest.mark.parametrize(
    "source, expected_results",
    (
        (
            "https://github.com/mozilla-mobile/fenix/blob/1b204158e5babdf25485063bdf3a449eff33e9cd/taskcluster/ci/version-bump",
            "https://github.com/mozilla-mobile/fenix",
        ),
    ),
)
def test_get_metadata_source_repo(task_defn, source, expected_results):
    task_defn["metadata"]["source"] = source
    assert ttask.get_source_repo(task_defn) == expected_results


def test_get_source_repo_no_source(task_defn):
    del task_defn["metadata"]["source"]
    with pytest.raises(TaskVerificationError):
        ttask.get_source_repo(task_defn)
    del task_defn["metadata"]
    with pytest.raises(TaskVerificationError):
        ttask.get_source_repo(task_defn)


def test_get_short_source_repo(task_defn):
    assert ttask.get_short_source_repo(task_defn) == "firefox-ios"


@pytest.mark.parametrize(
    "source_repo",
    (
        "https://github.com/mozilla-mobile/firefox-ios",
        "https://github.com/mozilla-mobile/reference-browser",
    ),
)
def test_get_payload_source_repo(task_defn, source_repo):
    task_defn["payload"]["source_repo"] = source_repo
    assert source_repo == ttask.get_source_repo(task_defn)


@pytest.mark.parametrize(
    "branch, expected_result",
    (
        ("foo", "foo"),
        ("refs/heads/foo", "foo"),
        (None, None),
    ),
)
def test_get_branch(task_defn, branch, expected_result):
    if branch:
        task_defn["payload"]["branch"] = branch
    assert ttask.get_branch(task_defn) == expected_result


@pytest.mark.parametrize(
    "bump_info",
    (
        {"next_version": "1.2.4", "files": ["version.txt"]},
        {"next_version": "98.0", "files": ["firefox-ios/Client/Configuration/version.xcconfig"]},
    ),
)
def test_bump_info(task_defn, bump_info):
    task_defn["payload"]["version_bump_info"] = bump_info
    tested_info = ttask.get_version_bump_info(task_defn)
    assert tested_info == bump_info


def test_bump_missing_bump_info(task_defn):
    with pytest.raises(TaskVerificationError):
        ttask.get_version_bump_info(task_defn)


@pytest.mark.parametrize("dontbuild", (True, False))
def test_get_dontbuild(task_defn, dontbuild):
    if dontbuild:
        task_defn["payload"]["dontbuild"] = True
    assert ttask.get_dontbuild(task_defn) == dontbuild


@pytest.mark.parametrize(
    "task,expected",
    (
        pytest.param(
            {
                "scopes": [
                    "project:mobile:foo:treescript:action:version_bump",
                ]
            },
            {"version_bump"},
            id="mobile_ok",
        ),
        pytest.param(
            {
                "scopes": [
                    "project:mobile:bar:treescript:action:version_bump",
                    "project:comm:foo:treescript:action:version_bump",
                ]
            },
            TaskVerificationError,
            id="mobile_missing",
        ),
        pytest.param(
            {
                "scopes": [
                    "project:mobile:foo:treescript:action:tag",
                ]
            },
            TaskVerificationError,
            id="mobile_invalid",
        ),
    ),
)
def test_task_action_types_scopes(config, task, expected):
    task.setdefault("payload", {}).setdefault("source_repo", "https://github.com/mobile/foo")

    config["trust_domain"] = "mobile"
    config["taskcluster_scope_prefix"] = "project:mobile:{repo}:treescript:"

    if inspect.isclass(expected) and issubclass(expected, Exception):
        with pytest.raises(expected):
            ttask.task_action_types(config, task)
    else:
        actions = ttask.task_action_types(config, task)
        assert actions == expected


@pytest.mark.parametrize("task", ({"payload": {"dry_run": False}},))
def test_should_push_true(task):
    assert True is ttask.should_push(task)


@pytest.mark.parametrize("task", ({"payload": {"dry_run": True}},))
def test_should_push_false(task):
    assert False is ttask.should_push(task)

