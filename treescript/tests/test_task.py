import os

import pytest

import treescript.task as ttask
from scriptworker_client.client import verify_task_schema
from scriptworker_client.exceptions import TaskVerificationError
from treescript.script import get_default_config

TEST_ACTION_TAG = "project:releng:treescript:action:tagging"
TEST_ACTION_BUMP = "project:releng:treescript:action:version_bump"
TEST_ACTION_INVALID = "project:releng:treescript:action:invalid"

SCRIPT_CONFIG = {"taskcluster_scope_prefix": "project:releng:treescript:"}


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
        "metadata": {"source": "https://hg.mozilla.org/releases/mozilla-test-source" "/file/1b4ab9a276ce7bb217c02b83057586e7946860f9/taskcluster/ci/foobar"},
    }


@pytest.yield_fixture(scope="function")
def config(tmpdir):
    config_ = get_default_config()
    config_["work_dir"] = os.path.join(tmpdir, "work")
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
    "source_repo",
    (
        "https://hg.mozilla.org/mozilla-central",
        "https://hg.mozilla.org/releases/mozilla-release",
        "https://hg.mozilla.org/releases/mozilla-esr120",
        "https://hg.mozilla.org/projects/mozilla-test-bed",
    ),
)
def test_get_metadata_source_repo(task_defn, source_repo):
    task_defn["metadata"]["source"] = "{}/file/default/taskcluster/ci/foobar".format(source_repo)
    assert source_repo == ttask.get_source_repo(task_defn)


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


@pytest.mark.parametrize("branch", ("foo", None))
def test_get_branch(task_defn, branch):
    if branch:
        task_defn["payload"]["branch"] = branch
    assert ttask.get_branch(task_defn) == branch


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
                "revision_url": "https://l10n.mozilla.org/shipping/l10n-changesets?av=fennec%(MAJOR_VERSION)s",
                "platform_configs": [{"platforms": ["android-multilocale"], "path": "mobile/android/locales/maemo-locales"}],
            }
        ],
        [
            {
                "path": "browser/locales/l10n-changesets.json",
                "name": "Firefox l10n changesets",
                "version_path": "browser/config/version.txt",
                "revision_url": "https://l10n.mozilla.org/shipping/l10n-changesets?av=fx%(MAJOR_VERSION)s",
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
    assert actions == ttask.task_action_types(SCRIPT_CONFIG, task)


@pytest.mark.parametrize(
    "actions,scopes",
    ((["tagging"], [TEST_ACTION_TAG]), (["version_bump"], [TEST_ACTION_BUMP]), (["tagging", "version_bump"], [TEST_ACTION_BUMP, TEST_ACTION_TAG])),
)
def test_task_action_types_valid_scopes(actions, scopes):
    task = {"scopes": scopes}
    assert actions == ttask.task_action_types(SCRIPT_CONFIG, task)


@pytest.mark.parametrize("scopes", ([TEST_ACTION_INVALID], [TEST_ACTION_TAG, TEST_ACTION_INVALID]))
def test_task_action_types_invalid_action(scopes):
    task = {"scopes": scopes}
    with pytest.raises(TaskVerificationError):
        ttask.task_action_types(SCRIPT_CONFIG, task)


@pytest.mark.parametrize("scopes", ([], ["project:releng:foo:not:for:here"]))
def test_task_action_types_missing_action(scopes):
    task = {"scopes": scopes}
    with pytest.raises(TaskVerificationError):
        ttask.task_action_types(SCRIPT_CONFIG, task)


@pytest.mark.parametrize("task", ({"payload": {}}, {"payload": {"dry_run": False}}, {"scopes": ["foo"]}))
def test_is_dry_run(task):
    assert False is ttask.is_dry_run(task)


def test_is_dry_run_true():
    task = {"payload": {"dry_run": True}}
    assert True is ttask.is_dry_run(task)
