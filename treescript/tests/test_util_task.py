import inspect
import os

import pytest
from scriptworker_client.client import verify_task_schema
from scriptworker_client.exceptions import TaskVerificationError
import yaml

from treescript.util import task as ttask
from treescript.script import get_default_config

SCRIPT_CONFIG = {"trust_domain": "gecko", "taskcluster_scope_prefix": "project:releng:treescript:"}


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
        "scopes": ["tagging"],
        "payload": {
            "upstreamArtifacts": [
                {"taskType": "build", "taskId": "VALID_TASK_ID", "formats": ["gpg"], "paths": ["public/build/firefox-52.0a1.en-US.win64.installer.exe"]}
            ]
        },
        "metadata": {"source": "https://hg.mozilla.org/releases/mozilla-test-source/file/1b4ab9a276ce7bb217c02b83057586e7946860f9/taskcluster/ci/foobar"},
    }


@pytest.fixture(scope="function")
def merge_day_task_defn(task_defn):
    with open(os.path.join(os.path.dirname(__file__), "data", "gecko_merge_example.yml")) as payload:
        task_defn["payload"] = yaml.safe_load(payload)
    return task_defn


@pytest.fixture(scope="function")
def config(tmpdir):
    config_ = get_default_config()
    config_["work_dir"] = os.path.join(tmpdir, "work")
    config_["trust_domain"] = "gecko"
    yield config_


# verify_task_schema {{{1
def test_missing_mandatory_urls_are_reported(config, task_defn):
    del task_defn["scopes"]

    with pytest.raises(TaskVerificationError):
        verify_task_schema(config, task_defn)


@pytest.mark.parametrize(
    "tag_info",
    (
        {"revision", "foobar"},
        {"tags": "some_string"},
        {"tags": ["some_string"]},
        {"tags": "somestring", "revision": "foobar"},
        {"tags": [], "revision": "foobar"},
        {"tags": [1], "revision": "foobar"},
        {"tags": ["tag", -1], "revision": "foobar"},
        {"tags": ["mercury"], "revision": 6},
    ),
)
def test_tag_info_invalid(config, task_defn, tag_info):
    task = task_defn
    task["payload"]["tag_info"] = tag_info
    with pytest.raises(TaskVerificationError):
        verify_task_schema(config, task)


def test_no_error_is_reported_when_no_missing_url(config, task_defn):
    verify_task_schema(config, task_defn)


def test_no_error_merge_day_schema(config, merge_day_task_defn):
    verify_task_schema(config, merge_day_task_defn)


@pytest.mark.parametrize(
    "source_url,raises",
    (
        ("https://bitbucket.org/mozilla/mozilla-central/file/foobar", TaskVerificationError),
        ("http://hg.mozilla.org/releases/mozilla-test-source/file/default/taskcluster/ci/foobar", TaskVerificationError),
        ("https://hg.mozilla.org/releases/mozilla-test-source/raw-file/default/taskcluster/ci/foobar", TaskVerificationError),
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
            "https://hg.mozilla.org/mozilla-central/file/default/taskcluster/ci/foobar",
            "https://hg.mozilla.org/mozilla-central",
        ),
        (
            "https://hg.mozilla.org/releases/mozilla-release/file/default/taskcluster/ci/foobar",
            "https://hg.mozilla.org/releases/mozilla-release",
        ),
        (
            "https://hg.mozilla.org/releases/mozilla-esr120/file/default/taskcluster/ci/foobar",
            "https://hg.mozilla.org/releases/mozilla-esr120",
        ),
        (
            "https://hg.mozilla.org/projects/mozilla-test-bed/file/default/taskcluster/ci/foobar",
            "https://hg.mozilla.org/projects/mozilla-test-bed",
        ),
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
    assert ttask.get_short_source_repo(task_defn) == "mozilla-test-source"


@pytest.mark.parametrize(
    "source_repo",
    (
        "https://hg.mozilla.org/mozilla-central",
        "https://hg.mozilla.org/releases/mozilla-release",
        "https://hg.mozilla.org/releases/mozilla-esr120",
        "https://hg.mozilla.org/projects/mozilla-test-bed",
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


@pytest.mark.parametrize("config", ({}, {"dummy": 1}))
def test_get_merge_config(task_defn, config):
    task_defn["payload"]["merge_info"] = config
    assert ttask.get_merge_config(task_defn) == config


def test_get_merge_config_missing(task_defn):
    with pytest.raises(TaskVerificationError):
        ttask.get_merge_config(task_defn)


@pytest.mark.parametrize(
    "tag_info", ({"revision": "deadbeef", "tags": ["FIREFOX_54.0b3_RELEASE", "BOB"]}, {"revision": "beef0001", "tags": ["FIREFOX_59.0b3_RELEASE", "FRED"]})
)
def test_tag_info(task_defn, tag_info):
    task_defn["payload"]["tag_info"] = tag_info
    tested_info = ttask.get_tag_info(task_defn)
    assert tested_info == tag_info


def test_tag_missing_tag_info(task_defn):
    with pytest.raises(TaskVerificationError):
        ttask.get_tag_info(task_defn)


@pytest.mark.parametrize(
    "bump_info",
    (
        {"next_version": "1.2.4", "files": ["browser/config/version.txt"]},
        {"next_version": "98.0.1b3", "files": ["config/milestone.txt", "browser/config/version_display.txt"]},
    ),
)
def test_bump_info(task_defn, bump_info):
    task_defn["payload"]["version_bump_info"] = bump_info
    tested_info = ttask.get_version_bump_info(task_defn)
    assert tested_info == bump_info


def test_bump_missing_bump_info(task_defn):
    with pytest.raises(TaskVerificationError):
        ttask.get_version_bump_info(task_defn)


@pytest.mark.parametrize(
    "l10n_bump_info",
    (
        [
            {
                "path": "mobile/locales/l10n-changesets.json",
                "name": "Fennec l10n changesets",
                "version_path": "mobile/android/config/version-files/beta/version.txt",
                "l10n_repo_url": "https://hg.mozilla.org/l10n-central/%(locale)s/json-pushes?version=2&tipsonly=1",
                "platform_configs": [{"platforms": ["android-multilocale"], "path": "mobile/android/locales/maemo-locales"}],
            }
        ],
        [
            {
                "path": "browser/locales/l10n-changesets.json",
                "name": "Firefox l10n changesets",
                "version_path": "browser/config/version.txt",
                "l10n_repo_url": "https://hg.mozilla.org/l10n-central/%(locale)s/json-pushes?version=2&tipsonly=1",
                "ignore_config": {
                    "ja": ["macosx64", "macosx64-devedition"],
                    "ja-JP-mac": [
                        "linux",
                        "linux-devedition",
                        "linux64",
                        "linux64-devedition",
                        "win32",
                        "win32-devedition",
                        "win64",
                        "win64-devedition",
                        "win64-aarch64",
                        "win64-aarch64-devedition",
                    ],
                },
                "platform_configs": [
                    {
                        "platforms": [
                            "linux",
                            "linux-devedition",
                            "linux64",
                            "linux64-devedition",
                            "macosx64",
                            "macosx64-devedition",
                            "win32",
                            "win32-devedition",
                            "win64",
                            "win64-devedition",
                            "win64-aarch64",
                            "win64-aarch64-devedition",
                        ],
                        "path": "browser/locales/shipped-locales",
                        "format": "shipped-locales",
                    }
                ],
            }
        ],
    ),
)
def test_get_l10n_bump_info(task_defn, l10n_bump_info):
    task_defn["payload"]["l10n_bump_info"] = l10n_bump_info
    tested_info = ttask.get_l10n_bump_info(task_defn)
    assert tested_info == l10n_bump_info


def test_missing_l10n_bump_info(task_defn):
    with pytest.raises(TaskVerificationError):
        ttask.get_l10n_bump_info(task_defn)


@pytest.mark.parametrize("dontbuild", (True, False))
def test_get_dontbuild(task_defn, dontbuild):
    if dontbuild:
        task_defn["payload"]["dontbuild"] = True
    assert ttask.get_dontbuild(task_defn) == dontbuild


@pytest.mark.parametrize("closed_tree", (True, False))
def test_get_ignore_closed_tree(task_defn, closed_tree):
    if closed_tree:
        task_defn["payload"]["ignore_closed_tree"] = True
    assert ttask.get_ignore_closed_tree(task_defn) == closed_tree


# task_task_action_types {{{1
@pytest.mark.parametrize("actions", (["tag"], ["version_bump"], ["tag", "version_bump", "push"]))
def test_task_action_types_actions(actions):
    task = {"payload": {"actions": actions}}
    assert set(actions) == ttask.task_action_types(SCRIPT_CONFIG, task)


# task_task_action_types {{{1
@pytest.mark.parametrize("actions", (["tag", "invalid"], ["invalid"]))
def test_task_action_types_actions_invalid(actions):
    task = {"payload": {"actions": actions}}
    with pytest.raises(TaskVerificationError):
        ttask.task_action_types(SCRIPT_CONFIG, task)


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


@pytest.mark.parametrize("ssh_user,expected", ((None, "default"), ("merge_user", "merge_user")))
def test_get_ssh_user(task_defn, ssh_user, expected):
    if ssh_user:
        task_defn["payload"]["ssh_user"] = ssh_user
    assert ttask.get_ssh_user(task_defn) == expected
