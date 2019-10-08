import aiohttp
import os
import pytest

from scriptworker.client import validate_task_schema
from scriptworker.exceptions import ScriptWorkerTaskException, TaskVerificationError

from signingscript.exceptions import SigningServerError
from signingscript.utils import mkdir
import signingscript.task as stask
from conftest import noop_sync, BASE_DIR

# helper constants, fixtures, functions {{{1
SERVER_CONFIG_PATH = os.path.join(BASE_DIR, "example_server_config.json")
DEFAULT_SCOPE_PREFIX = "project:releng:signing:"
TEST_CERT_TYPE = "{}cert:dep-signing".format(DEFAULT_SCOPE_PREFIX)
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
                {
                    "taskType": "build",
                    "taskId": "VALID_TASK_ID",
                    "formats": ["gpg"],
                    "paths": ["public/build/firefox-52.0a1.en-US.win64.installer.exe"],
                }
            ]
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


# task_signing_formats {{{1
def test_task_signing_formats(context):
    context.task = {
        "payload": {"upstreamArtifacts": [{"formats": ["mar", "gpg"]}]},
        "scopes": [TEST_CERT_TYPE],
    }
    assert {"mar", "gpg"} == stask.task_signing_formats(context)


def test_task_signing_formats_support_several_projects(context):
    context.config["taskcluster_scope_prefixes"] = [
        "project:mobile:focus:releng:signing:",
        "project:mobile:fenix:releng:signing:",
    ]

    context.task = {
        "payload": {"upstreamArtifacts": [{"formats": ["focus-jar"]}]},
        "scopes": ["project:mobile:focus:releng:signing:cert:dep-signing"],
    }
    assert {"focus-jar"} == stask.task_signing_formats(context)

    context.task = {
        "payload": {"upstreamArtifacts": [{"formats": ["autograph_fenix"]}]},
        "scopes": ["project:mobile:fenix:releng:signing:cert:dep-signing"],
    }
    assert {"autograph_fenix"} == stask.task_signing_formats(context)


def test_task_cert_errors_when_2_different_projects_are_signed_in_the_same_task(
    context
):
    context.config["taskcluster_scope_prefixes"] = [
        "project:mobile:focus:releng:signing:",
        "project:mobile:fenix:releng:signing:",
    ]
    context.task = {
        "scopes": [
            "project:mobile:focus:releng:signing:cert:dep-signing",
            "project:mobile:fenix:releng:signing:cert:dep-signing",
        ]
    }
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


# get_token {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc,contents", ((ScriptWorkerTaskException, "token"), (None, ""), (None, "token"))
)
async def test_get_token(mocker, tmpdir, exc, contents, context):
    async def test_token(*args, **kwargs):
        if exc:
            raise exc("Expected exception")
        return contents

    output_file = os.path.join(tmpdir, "foo")
    mocker.patch.object(aiohttp, "BasicAuth", new=noop_sync)
    mocker.patch.object(stask, "retry_request", new=test_token)
    if exc or not contents:
        with pytest.raises(SigningServerError):
            await stask.get_token(context, output_file, TEST_CERT_TYPE, ["gpg"])
    else:
        await stask.get_token(context, output_file, TEST_CERT_TYPE, ["gpg"])
        with open(output_file, "r") as fh:
            assert fh.read().rstrip() == contents


# sign {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "format,filename,post_files",
    (
        ("gpg", "filename", ["filename", "filename.asc"]),
        ("sha2signcode", "file.zip", ["file.zip"]),
    ),
)
async def test_sign(context, mocker, format, filename, post_files):
    async def fake_gpg(_, path, *kwargs):
        return [path, "{}.asc".format(path)]

    async def fake_other(_, path, *kwargs):
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
        ("autograph_focus", stask.sign_jar),
        ("autograph_hash_only_mar384", stask.sign_mar384_with_autograph_hash),
        ("gpg", stask.sign_gpg),
        ("jar", stask.sign_jar),
        ("focus-jar", stask.sign_jar),
        ("macapp", stask.sign_macapp),
        ("osslsigncode", stask.sign_signcode),
        ("sha2signcode", stask.sign_signcode),
        ("signcode", stask.sign_signcode),
        ("widevine", stask.sign_widevine),
        ("widevine_blessed", stask.sign_widevine),
        ("default", stask.sign_file),
        # Regex cases
        ("autograph_apk_fenix", stask.sign_jar),
        ("autograph_apk_fennec_sha1", stask.sign_jar),
        ("autograph_apk_focus", stask.sign_jar),
        ("autograph_apk_reference_browser", stask.sign_jar),
        (
            "autograph_hash_only_mar384:firefox_20190321_dev",
            stask.sign_mar384_with_autograph_hash,
        ),
        # Default
        ("autograph_apk_", stask.sign_file),
        ("non-existing-format", stask.sign_file),
    ),
)
def test_get_signing_function_from_format(format, expected):
    assert stask._get_signing_function_from_format(format) == expected


# build_filelist_dict {{{1
def test_build_filelist_dict(context, task_defn):
    full_path = os.path.join(
        context.config["work_dir"],
        "cot",
        "VALID_TASK_ID",
        "public/build/firefox-52.0a1.en-US.win64.installer.exe",
    )
    expected = {
        "public/build/firefox-52.0a1.en-US.win64.installer.exe": {
            "full_path": full_path,
            "formats": ["gpg"],
        }
    }
    context.task = task_defn

    # first, the file is missing...
    with pytest.raises(TaskVerificationError):
        stask.build_filelist_dict(context)

    mkdir(os.path.dirname(full_path))
    with open(full_path, "w") as fh:
        fh.write("foo")

    assert stask.build_filelist_dict(context) == expected
