import json
import os
import tempfile
from contextlib import nullcontext as does_not_raise

import pytest
from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException

from beetmoverscript.task import (
    add_balrog_manifest_to_artifacts,
    check_maven_artifact_map,
    generate_checksums_manifest,
    get_maven_version,
    get_release_props,
    get_schema_key_by_action,
    get_task_action,
    get_task_bucket,
    get_taskId_from_full_path,
    get_upstream_artifacts,
    is_custom_checksums_task,
    validate_task_schema,
)

from . import get_fake_checksums_manifest, get_fake_valid_config, get_fake_valid_task


# get_schema_key_by_action {{{1
@pytest.mark.parametrize(
    "scopes, expected",
    (
        (["project:releng:beetmover:bucket:maven-staging", "project:releng:beetmover:action:push-to-maven"], "maven_schema_file"),
        (["project:releng:beetmover:bucket:dep", "project:releng:beetmover:action:push-to-releases"], "release_schema_file"),
        (["project:releng:beetmover:bucket:dep", "project:releng:beetmover:action:push-to-candidates"], "schema_file"),
        (["project:releng:beetmover:bucket:dep", "project:releng:beetmover:action:push-to-partner"], "schema_file"),
        (["project:releng:beetmover:bucket:dep", "project:releng:beetmover:action:push-to-nightly"], "schema_file"),
    ),
)
def test_get_schema_key_by_action(scopes, expected):
    context = Context()
    context.config = get_fake_valid_config()
    context.task = get_fake_valid_task()
    context.task["scopes"] = scopes

    assert expected == get_schema_key_by_action(context)


# get_upstream_artifacts {{{1
def test_exception_get_upstream_artifacts():
    context = Context()
    context.config = get_fake_valid_config()
    context.task = get_fake_valid_task()
    context.properties = context.task["payload"]["releaseProperties"]

    context.task["payload"]["upstreamArtifacts"][0]["paths"].append("fake_file")
    with pytest.raises(ScriptWorkerTaskException):
        context.artifacts_to_beetmove = get_upstream_artifacts(context)


# get_upstream_artifacts {{{1
@pytest.mark.parametrize(
    "expected, preserve",
    (
        (["target.txt", "target.mozinfo.json", "target_info.txt", "target.test_packages.json", "buildhub.json", "target.apk"], False),
        (
            [
                "public/build/target.txt",
                "public/build/target.mozinfo.json",
                "public/build/target_info.txt",
                "public/build/target.test_packages.json",
                "public/build/buildhub.json",
                "public/build/target.apk",
            ],
            True,
        ),
    ),
)
def test_get_upstream_artifacts(expected, preserve):
    context = Context()
    context.config = get_fake_valid_config()
    context.task = get_fake_valid_task()
    context.properties = context.task["payload"]["releaseProperties"]

    artifacts_to_beetmove = get_upstream_artifacts(context, preserve_full_paths=preserve)
    assert sorted(list(artifacts_to_beetmove["en-US"])) == sorted(expected)


# validate_task {{{1
def test_validate_task(context):
    validate_task_schema(context)

    # release validation
    context.task["scopes"] = ["project:releng:beetmover:action:push-to-releases"]
    context.task["payload"] = {"product": "fennec", "build_number": 1, "version": "64.0b3"}
    validate_task_schema(context)


# get_task_bucket {{{1
@pytest.mark.parametrize(
    "scopes,expected,raises",
    (
        (["project:releng:beetmover:bucket:dep", "project:releng:beetmover:bucket:release"], None, True),
        (["project:releng:beetmover:bucket:!!"], None, True),
        (["project:releng:beetmover:bucket:dep", "project:releng:beetmover:action:foo"], "dep", False),
    ),
)
def test_get_task_bucket(scopes, expected, raises):
    task = {"scopes": scopes}
    config = {"bucket_config": {"dep": ""}, "taskcluster_scope_prefixes": ["project:releng:beetmover:"]}
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            get_task_bucket(task, config)
    else:
        assert expected == get_task_bucket(task, config)


# get_task_action {{{1
@pytest.mark.parametrize(
    "scopes,expected,raises",
    (
        (["project:releng:beetmover:action:push-to-nightly", "project:releng:beetmover:action:invalid"], None, True),
        (["project:releng:beetmover:action:invalid"], None, True),
        (["project:releng:beetmover:action:push-to-nightly"], "push-to-nightly", False),
    ),
)
def test_get_task_action(scopes, expected, raises):
    task = {"scopes": scopes}
    config = {"actions": {"dep": ""}, "taskcluster_scope_prefixes": ["project:releng:beetmover:"]}
    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            get_task_action(task, config, valid_actions=["push-to-nightly"])
    else:
        assert expected == get_task_action(task, config)


@pytest.mark.parametrize(
    "appName,appVersion,payload_version,buildid,expected,raises",
    (
        ("components", None, "63.0.20201013153553", "20201013153553", "63.0.20201013153553", False),
        ("components", None, "63.0.0-TESTING", "not-important", None, True),
        ("geckoview", "83.0a1", "83.0a1", "20200920201111", "83.0.20200920201111", False),  # Tests special case
        ("geckoview", "84.0b2", "84.0.20200920201111", "not-important", "84.0.20200920201111", False),
        ("geckoview", "83.0a1", "83.0.0-TESTING", "0-TESTING", None, True),
        ("geckoview", "84.0b2", "84.0.0-TESTING", "0-TESTING", None, True),
    ),
)
def test_get_maven_version(context, appName, appVersion, payload_version, buildid, expected, raises):
    context.release_props["appName"] = appName
    if appVersion is not None:
        context.release_props["appVersion"] = appVersion
    context.release_props["buildid"] = buildid
    context.task["payload"]["version"] = payload_version

    if raises:
        with pytest.raises(ScriptWorkerTaskException):
            get_maven_version(context)
    else:
        assert expected == get_maven_version(context)


@pytest.mark.parametrize(
    "payload_version,filename_version,folder_version,expectation",
    (
        ("12.3.20200920201111", "12.3.20200920201111", "12.3.20200920201111", does_not_raise()),
        ("12.3.20200920201111", "a.bad.version", "12.3.20200920201111", pytest.raises(ScriptWorkerTaskException)),
        ("12.3.20200920201111", "12.3.20200920201111", "a.bad.version", pytest.raises(ScriptWorkerTaskException)),
    ),
)
def test_check_maven_artifact_map(context, payload_version, filename_version, folder_version, expectation):
    context.action = "push-to-maven"
    source = "fake_path/fake-artifact-{version}.jar"

    artifact_map_entry = {
        "locale": "en-US",
        "paths": {
            source: {
                "checksums_path": "",
                "destinations": [f"fake/destination/{folder_version}/fake-artifact-{filename_version}.jar"],
            }
        },
        "taskId": "fake-task-id",
    }

    context.task = {
        "payload": {
            "artifactMap": [artifact_map_entry],
            "releaseProperties": {"appName": "nightly_components"},
            "upstreamArtifacts": [{"paths": [source], "taskId": "fake-task-id", "taskType": "build"}],
            "version": payload_version,
        }
    }

    with expectation:
        check_maven_artifact_map(context, payload_version)


# balrog_manifest_to_artifacts {{{1
def test_balrog_manifest_to_artifacts():
    context = Context()
    context.task = get_fake_valid_task()
    context.config = get_fake_valid_config()

    fake_balrog_manifest = context.task["payload"]["releaseProperties"]
    context.balrog_manifest = fake_balrog_manifest

    # fake the path to to able to check the contents written later on
    with tempfile.TemporaryDirectory() as tmpdirname:
        context.config["artifact_dir"] = tmpdirname
        file_path = os.path.join(context.config["artifact_dir"], "public/manifest.json")
        # <temp-dir>/public doesn't exist yet and it's not automatically
        # being created so we need to ensure it exists
        public_tmpdirname = os.path.join(tmpdirname, "public")
        if not os.path.exists(public_tmpdirname):
            os.makedirs(public_tmpdirname)

        add_balrog_manifest_to_artifacts(context)

        with open(file_path, "r") as fread:
            retrieved_data = json.load(fread)

        assert fake_balrog_manifest == retrieved_data


# checksums_manifest_generation {{{1
def test_checksums_manifest_generation():
    checksums = {
        "firefox-53.0a1.en-US.linux-i686.complete.mar": {
            "sha512": "14f2d1cb999a8b42a3b6b671f7376c3e246daa65d108e2b8fe880f069601dc2b26afa155b52001235db059",
            "size": 618149,
            "sha256": "293975734953874539475",
        }
    }

    context = Context()
    context.task = get_fake_valid_task()
    context.config = get_fake_valid_config()
    context.checksums = checksums

    expected_checksums_manifest_dump = get_fake_checksums_manifest()
    checksums_manifest_dump = generate_checksums_manifest(context)
    assert checksums_manifest_dump == expected_checksums_manifest_dump


# get_release_props {{{1
@pytest.mark.parametrize(
    "taskjson,locale, relprops, expected",
    (
        ("task.json", False, {"platform": "android-api-16"}, {"platform": "android-api-16", "stage_platform": "android-api-16"}),
        ("task.json", True, {"platform": "macosx64"}, {"platform": "mac", "stage_platform": "macosx64"}),
        ("task.json", False, {"platform": "linux64"}, {"platform": "linux-x86_64", "stage_platform": "linux64"}),
        ("task_devedition.json", False, {"platform": "macosx64-devedition"}, {"platform": "mac", "stage_platform": "macosx64-devedition"}),
        ("task_devedition.json", True, {"platform": "win64-devedition"}, {"platform": "win64", "stage_platform": "win64-devedition"}),
    ),
)
def test_get_release_props(context, mocker, taskjson, locale, relprops, expected):
    context.task = get_fake_valid_task(taskjson)
    if locale:
        context.task["payload"]["locale"] = "lang"

    context.task["payload"]["releaseProperties"] = relprops
    assert get_release_props(context) == expected

    context.task["payload"]["releaseProperties"] = None
    with pytest.raises(ScriptWorkerTaskException):
        get_release_props(context)


# get_release_props {{{1
def test_get_release_props_raises(context, mocker):
    context.task = get_fake_valid_task(taskjson="task_missing_relprops.json")
    with pytest.raises(ScriptWorkerTaskException):
        get_release_props(context)


# is_custom_beetmover_checksums_task {{{1
@pytest.mark.parametrize("kind,expected", (("beetmover-source", "-source"), ("beetmover-repackage", ""), ("release-beetmover-signed-langpacks", "-langpack")))
def test_is_custom_beetmover_task(context, kind, expected):
    context.task["tags"]["kind"] = kind
    assert is_custom_checksums_task(context) == expected


@pytest.mark.parametrize(
    "path, expected",
    (
        ("/src/beetmoverscript/test/test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/target.mozinfo.json", "eSzfNqMZT_mSiQQXu8hyqg"),
        ("/src/beetmoverscript/test/test_work_dir/cot/eSzfNqMZT_mSiQQXu8cotg/public/build/target.mozinfo.json", "eSzfNqMZT_mSiQQXu8cotg"),
        ("test_work_dir/cot/eSzfNqMZT_mSiQQXu8hyqg/public/build/target.mozinfo.json", "eSzfNqMZT_mSiQQXu8hyqg"),
    ),
)
def test_get_taskId_from_full_path(path, expected):
    assert get_taskId_from_full_path(path) == expected


@pytest.mark.parametrize(
    "path",
    (
        ("test_work_dir/eSzfNqMZT_mSiQQXu8hyqg/public/build/target.mozinfo.json"),
        ("test_work_dir/cot"),
        ("/src/beetmoverscript/test/test_work_dir/cot/public/build/target.mozinfo.json"),
    ),
)
def test_get_taskId_from_full_path_raises(path):
    with pytest.raises(ScriptWorkerTaskException):
        get_taskId_from_full_path(path)
