import os

import pytest
from conftest import DEFAULT_SCOPE_PREFIX, TEST_CERT_TYPE
from scriptworker.client import validate_task_schema
from scriptworker.exceptions import ScriptWorkerTaskException, TaskVerificationError

import signingscript.task as stask
from signingscript.utils import mkdir

# helper constants, fixtures, functions {{{1
TEST_AUTOGRAPH_TYPE = "{}autograph:dep-signing".format(DEFAULT_SCOPE_PREFIX)


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
        "scopes": ["signing"],
        "payload": {
            "upstreamArtifacts": [
                {"taskType": "build", "taskId": "VALID_TASK_ID", "formats": ["gpg"], "paths": ["public/build/firefox-52.0a1.en-US.win64.installer.exe"]}
            ]
        },
    }


@pytest.fixture(scope="function")
def task_defn_authenticode_comment():
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
        "scopes": ["signing"],
        "payload": {
            "upstreamArtifacts": [
                {
                    "taskType": "build",
                    "taskId": "VALID_TASK_ID",
                    "formats": ["gpg"],
                    "paths": ["public/build/firefox-52.0a1.en-US.win64.installer.exe"],
                    "authenticode_comment": "Foo Installer",
                }
            ],
        },
    }


# task_cert_type {{{1
def test_task_cert_type(context):
    context.task = {"scopes": [TEST_CERT_TYPE]}
    assert TEST_CERT_TYPE == stask.task_cert_type(context)


def test_task_cert_type_error(context):
    context.task = {"scopes": [TEST_CERT_TYPE, "project:releng:signing:cert:notdep"]}
    with pytest.raises(ScriptWorkerTaskException):
        stask.task_cert_type(context)
    context.task = None
    with pytest.raises(TaskVerificationError):
        stask.task_cert_type(context)


# task_signing_formats {{{1
def test_task_signing_formats(context):
    context.task = {"payload": {"upstreamArtifacts": [{"formats": ["mar", "gpg"]}]}, "scopes": [TEST_CERT_TYPE]}
    assert {"mar", "gpg"} == stask.task_signing_formats(context)


def test_task_signing_formats_support_several_projects(context):
    context.config["taskcluster_scope_prefixes"] = ["project:mobile:firefox-android:releng:signing:", "project:mobile:fenix:releng:signing:"]

    context.task = {
        "payload": {"upstreamArtifacts": [{"formats": ["focus-jar"]}]},
        "scopes": ["project:mobile:firefox-android:releng:signing:cert:dep-signing"],
    }
    assert {"focus-jar"} == stask.task_signing_formats(context)

    context.task = {"payload": {"upstreamArtifacts": [{"formats": ["autograph_fenix"]}]}, "scopes": ["project:mobile:fenix:releng:signing:cert:dep-signing"]}
    assert {"autograph_fenix"} == stask.task_signing_formats(context)


def test_task_cert_errors_when_2_different_projects_are_signed_in_the_same_task(context):
    context.config["taskcluster_scope_prefixes"] = ["project:mobile:firefox-android:releng:signing:", "project:mobile:fenix:releng:signing:"]
    context.task = {"scopes": ["project:mobile:firefox-android:releng:signing:cert:dep-signing", "project:mobile:fenix:releng:signing:cert:dep-signing"]}
    with pytest.raises(TaskVerificationError):
        stask.task_cert_type(context)


# validate_task_schema {{{1
def test_missing_mandatory_urls_are_reported(context, task_defn):
    context.task = task_defn
    del context.task["scopes"]

    with pytest.raises(ScriptWorkerTaskException):
        validate_task_schema(context)


def test_no_error_is_reported_when_no_missing_url(context, task_defn):
    context.task = task_defn
    validate_task_schema(context)


# sign {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize("format,filename,post_files", (("gpg", "filename", ["filename", "filename.asc"]), ("sha2signcode", "file.zip", ["file.zip"])))
async def test_sign(context, mocker, format, filename, post_files):
    async def fake_gpg(_, path, *args, **kwargs):
        return [path, "{}.asc".format(path)]

    async def fake_other(_, path, *args, **kwargs):
        return path

    fake_format_to = {"gpg": fake_gpg, "default": fake_other}

    def fake_log(context, new_files, *args):
        assert new_files == post_files

    mocker.patch.object(stask, "FORMAT_TO_SIGNING_FUNCTION", new=fake_format_to)
    await stask.sign(context, filename, [format])


@pytest.mark.parametrize(
    "format, expected",
    (
        # Hardcoded cases
        ("autograph_apk_fennec_sha1", stask.sign_jar),
        ("autograph_hash_only_mar384", stask.sign_mar384_with_autograph_hash),
        ("gpg", stask.sign_gpg),
        ("jar", stask.sign_jar),
        ("focus-jar", stask.sign_jar),
        ("macapp", stask.sign_macapp),
        ("widevine", stask.sign_widevine),
        ("autograph_authenticode", stask.sign_authenticode),
        ("autograph_authenticode_stub", stask.sign_authenticode),
        ("default", stask.sign_file),
        # Key id cases
        ("autograph_hash_only_mar384:firefox_20190321_dev", stask.sign_mar384_with_autograph_hash),
        ("autograph_authenticode:202005", stask.sign_authenticode),
        ("autograph_authenticode_stub:202005", stask.sign_authenticode),
        # Default
        ("autograph_apk", stask.sign_file),
        ("autograph_focus", stask.sign_file),
        ("non-existing-format", stask.sign_file),
    ),
)
def test_get_signing_function_from_format(format, expected):
    assert stask._get_signing_function_from_format(format) == expected


# build_filelist_dict {{{1
def test_build_filelist_dict(context, task_defn):
    full_path = os.path.join(context.config["work_dir"], "cot", "VALID_TASK_ID", "public/build/firefox-52.0a1.en-US.win64.installer.exe")
    expected = {"public/build/firefox-52.0a1.en-US.win64.installer.exe": {"full_path": full_path, "formats": ["gpg"]}}
    context.task = task_defn

    # first, the file is missing...
    with pytest.raises(TaskVerificationError):
        stask.build_filelist_dict(context)

    mkdir(os.path.dirname(full_path))
    with open(full_path, "w") as fh:
        fh.write("foo")

    assert stask.build_filelist_dict(context) == expected


def test_build_filelist_dict_comment(context, task_defn_authenticode_comment):
    full_path = os.path.join(
        context.config["work_dir"],
        "cot",
        "VALID_TASK_ID",
        "public/build/firefox-52.0a1.en-US.win64.installer.msi",
    )
    expected = {
        "public/build/firefox-52.0a1.en-US.win64.installer.msi": {"full_path": full_path, "formats": ["autograph_authenticode"], "comment": "Foo Installer"}
    }
    context.task = task_defn_authenticode_comment

    # first, format is wrong...
    with pytest.raises(TaskVerificationError) as error:
        stask.build_filelist_dict(context)
    assert "without an authenticode" in str(error.value)

    # coerce to authenticode
    context.task["payload"]["upstreamArtifacts"][0]["formats"] = ["autograph_authenticode"]

    # Still raises due to no msi
    with pytest.raises(TaskVerificationError) as error:
        stask.build_filelist_dict(context)
    assert "outside of msi" in str(error.value)

    # coerce to msi
    context.task["payload"]["upstreamArtifacts"][0]["paths"] = [
        "public/build/firefox-52.0a1.en-US.win64.installer.msi",
    ]

    # the file is missing...
    with pytest.raises(TaskVerificationError):
        stask.build_filelist_dict(context)

    mkdir(os.path.dirname(full_path))
    with open(full_path, "w") as fh:
        fh.write("foo")

    # Now ok
    assert stask.build_filelist_dict(context) == expected
