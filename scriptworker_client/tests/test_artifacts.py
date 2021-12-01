import itertools
import json
import os

import mock
import pytest

import scriptworker_client.artifacts as swartifacts
from scriptworker_client.artifacts import (
    get_and_check_single_upstream_artifact_full_path,
    get_optional_artifacts_per_task_id,
    get_single_upstream_artifact_full_path,
    get_upstream_artifacts_full_paths_per_task_id,
)

from scriptworker_client.exceptions import TaskVerificationError

from . import touch


def test_get_upstream_artifacts_full_paths_per_task_id():
    artifacts_to_succeed = [
        {"paths": ["public/file_a1"], "taskId": "dependency1", "taskType": "signing"},
        {
            "paths": ["public/file_b1", "public/file_b2"],
            "taskId": "dependency2",
            "taskType": "signing",
        },
        {
            "paths": ["some_other_folder/file_c"],
            "taskId": "dependency3",
            "taskType": "signing",
        },
        {
            # Case where the same taskId was given. In some occasion we may want to split
            # upstreamArtifacts of the same taskId into 2. For instance: 1 taskId with a given
            # parameter (like beetmover's "locale") but not the other
            "paths": ["public/file_a2"],
            "taskId": "dependency1",
            "taskType": "signing",
        },
    ]

    task = {}
    task["payload"] = {
        "upstreamArtifacts": [
            {
                "paths": ["public/failed_optional_file1"],
                "taskId": "failedDependency1",
                "taskType": "signing",
                "optional": True,
            },
            {
                "paths": [
                    "public/failed_optional_file2",
                    "public/failed_optional_file3",
                ],
                "taskId": "failedDependency2",
                "taskType": "signing",
                "optional": True,
            },
        ]
    }
    config = {}
    config["work_dir"] = os.path.abspath("some/path")

    task["payload"]["upstreamArtifacts"].extend(artifacts_to_succeed)
    for artifact in artifacts_to_succeed:
        folder = os.path.join(config["work_dir"], "cot", artifact["taskId"])

        for path in artifact["paths"]:
            try:
                os.makedirs(os.path.join(folder, os.path.dirname(path)))
            except FileExistsError:
                pass
            touch(os.path.join(folder, path))

    (
        succeeded_artifacts,
        failed_artifacts,
    ) = get_upstream_artifacts_full_paths_per_task_id(config, task)

    assert succeeded_artifacts == {
        "dependency1": [
            os.path.join(config["work_dir"], "cot", "dependency1", "public", "file_a1"),
            os.path.join(config["work_dir"], "cot", "dependency1", "public", "file_a2"),
        ],
        "dependency2": [
            os.path.join(config["work_dir"], "cot", "dependency2", "public", "file_b1"),
            os.path.join(config["work_dir"], "cot", "dependency2", "public", "file_b2"),
        ],
        "dependency3": [
            os.path.join(
                config["work_dir"], "cot", "dependency3", "some_other_folder", "file_c"
            )
        ],
    }
    assert failed_artifacts == {
        "failedDependency1": ["public/failed_optional_file1"],
        "failedDependency2": [
            "public/failed_optional_file2",
            "public/failed_optional_file3",
        ],
    }


def test_fail_get_upstream_artifacts_full_paths_per_task_id():
    task = {}
    task["payload"] = {
        "upstreamArtifacts": [
            {
                "paths": ["public/failed_mandatory_file"],
                "taskId": "failedDependency",
                "taskType": "signing",
            }
        ]
    }
    config = {}
    config["work_dir"] = os.path.abspath("some/path")
    with pytest.raises(TaskVerificationError):
        get_upstream_artifacts_full_paths_per_task_id(config, task)


def test_get_and_check_single_upstream_artifact_full_path():
    task = {}
    config = {}
    config["work_dir"] = os.path.abspath("some/path")
    folder = os.path.join(config["work_dir"], "cot", "dependency1")
    touch(os.path.join(folder, "public/file_a"))

    assert get_and_check_single_upstream_artifact_full_path(
        config, "dependency1", "public/file_a"
    ) == os.path.join(config["work_dir"], "cot", "dependency1", "public", "file_a")

    with pytest.raises(TaskVerificationError):
        get_and_check_single_upstream_artifact_full_path(
            config, "dependency1", "public/non_existing_file"
        )

    with pytest.raises(TaskVerificationError):
        get_and_check_single_upstream_artifact_full_path(
            config, "non-existing-dep", "public/file_a"
        )


def test_get_single_upstream_artifact_full_path():
    config = {}
    config["work_dir"] = os.path.abspath("some/path")
    os.path.join(config["work_dir"], "cot", "dependency1")

    assert get_single_upstream_artifact_full_path(
        config, "dependency1", "public/file_a"
    ) == os.path.join(config["work_dir"], "cot", "dependency1", "public", "file_a")

    assert get_single_upstream_artifact_full_path(
        config, "dependency1", "public/non_existing_file"
    ) == os.path.join(
        config["work_dir"], "cot", "dependency1", "public", "non_existing_file"
    )

    assert get_single_upstream_artifact_full_path(
        config, "non-existing-dep", "public/file_a"
    ) == os.path.join(config["work_dir"], "cot", "non-existing-dep", "public", "file_a")


@pytest.mark.parametrize(
    "upstream_artifacts, expected",
    (
        ([{}], {}),
        ([{"taskId": "someTaskId", "paths": ["mandatory_artifact_1"]}], {}),
        (
            [
                {
                    "taskId": "someTaskId",
                    "paths": ["optional_artifact_1"],
                    "optional": True,
                }
            ],
            {"someTaskId": ["optional_artifact_1"]},
        ),
        (
            [
                {
                    "taskId": "someTaskId",
                    "paths": ["optional_artifact_1", "optional_artifact_2"],
                    "optional": True,
                }
            ],
            {"someTaskId": ["optional_artifact_1", "optional_artifact_2"]},
        ),
        (
            [
                {
                    "taskId": "someTaskId",
                    "paths": ["optional_artifact_1"],
                    "optional": True,
                },
                {
                    "taskId": "someOtherTaskId",
                    "paths": ["optional_artifact_2"],
                    "optional": True,
                },
                {"taskId": "anotherOtherTaskId", "paths": ["mandatory_artifact_1"]},
            ],
            {
                "someTaskId": ["optional_artifact_1"],
                "someOtherTaskId": ["optional_artifact_2"],
            },
        ),
        (
            [
                {
                    "taskId": "taskIdGivenThreeTimes",
                    "paths": ["optional_artifact_1"],
                    "optional": True,
                },
                {"taskId": "taskIdGivenThreeTimes", "paths": ["mandatory_artifact_1"]},
                {
                    "taskId": "taskIdGivenThreeTimes",
                    "paths": ["optional_artifact_2"],
                    "optional": True,
                },
            ],
            {"taskIdGivenThreeTimes": ["optional_artifact_1", "optional_artifact_2"]},
        ),
    ),
)
def test_get_optional_artifacts_per_task_id(upstream_artifacts, expected):
    assert get_optional_artifacts_per_task_id(upstream_artifacts) == expected


# assert_is_parent {{{1
@pytest.mark.parametrize(
    "path, parent_path, raises",
    (
        ("/foo/bar/baz", "/foo/bar", False),
        ("/foo", "/foo/bar", True),
        ("/foo/bar/..", "/foo/bar", True),
    ),
)
def test_assert_is_parent(path, parent_path, raises):
    if raises:
        with pytest.raises(TaskVerificationError):
            swartifacts.assert_is_parent(path, parent_path)
    else:
        swartifacts.assert_is_parent(path, parent_path)


def test_assert_is_parent_softlink(tmpdir):
    """A softlink that points outside of a parent_dir is not under parent_dir."""
    work_dir = os.path.join(tmpdir, "work")
    external_dir = os.path.join(tmpdir, "external")
    os.mkdir(work_dir)
    os.mkdir(external_dir)
    link = os.path.join(work_dir, "link")
    os.symlink(external_dir, link)
    with pytest.raises(TaskVerificationError):
        swartifacts.assert_is_parent(link, work_dir)
