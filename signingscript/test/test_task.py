import aiohttp
import os
import pytest

from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException

from signingscript.exceptions import SigningServerError, TaskVerificationError
from signingscript.script import get_default_config
from signingscript.utils import load_signing_server_config, mkdir
import signingscript.task as stask
from signingscript.test import noop_sync, tmpdir

assert tmpdir  # silence flake8


# helper constants, fixtures, functions {{{1
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SERVER_CONFIG_PATH = os.path.join(BASE_DIR, 'example_server_config.json')
TEST_CERT_TYPE = "project:releng:signing:cert:dep-signing"


@pytest.fixture(scope='function')
def task_defn():
    return {
        'provisionerId': 'meh',
        'workerType': 'workertype',
        'schedulerId': 'task-graph-scheduler',
        'taskGroupId': 'some',
        'routes': [],
        'retries': 5,
        'created': '2015-05-08T16:15:58.903Z',
        'deadline': '2015-05-08T18:15:59.010Z',
        'expires': '2016-05-08T18:15:59.010Z',
        'dependencies': ['VALID_TASK_ID'],
        'scopes': ['signing'],
        'payload': {
          'upstreamArtifacts': [{
            'taskType': 'build',
            'taskId': 'VALID_TASK_ID',
            'formats': ['gpg'],
            'paths': ['public/build/firefox-52.0a1.en-US.win64.installer.exe'],
          }]
        }
    }


@pytest.yield_fixture(scope='function')
def context(tmpdir):
    context = Context()
    context.config = get_default_config()
    context.config['signing_server_config'] = SERVER_CONFIG_PATH
    context.config['work_dir'] = os.path.join(tmpdir, 'work')
    context.config['artifact_dir'] = os.path.join(tmpdir, 'artifact')
    context.signing_servers = load_signing_server_config(context)
    yield context


# task_signing_formats {{{1
def test_task_signing_formats():
    task = {"scopes": [TEST_CERT_TYPE,
                       "project:releng:signing:format:mar",
                       "project:releng:signing:format:gpg"]}
    assert ["mar", "gpg"] == stask.task_signing_formats(task)


# validate_task_schema {{{1
def test_missing_mandatory_urls_are_reported(context, task_defn):
    context.task = task_defn
    del(context.task['scopes'])

    with pytest.raises(ScriptWorkerTaskException):
        stask.validate_task_schema(context)


def test_no_error_is_reported_when_no_missing_url(context, task_defn):
    context.task = task_defn
    stask.validate_task_schema(context)


# get_token {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize('exc,contents', ((
    ScriptWorkerTaskException, 'token'
), (
    None, ''
), (
    None, 'token'
)))
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
@pytest.mark.parametrize('format,filename,post_files', ((
    'gpg', 'filename', ['filename', 'filename.asc']
), (
    'sha2signcode', 'file.zip', ['file.zip']
)))
async def test_sign(context, mocker, format, filename, post_files):

    async def fake_gpg(_, path, *kwargs):
        return [path, "{}.asc".format(path)]

    async def fake_other(_, path, *kwargs):
        return path

    fake_format_to = {
        "gpg": fake_gpg,
        "default": fake_other,
    }

    def fake_log(context, new_files, *args):
        assert new_files == post_files

    mocker.patch.object(stask, 'FORMAT_TO_SIGNING_FUNCTION', new=fake_format_to)
    mocker.patch.object(stask, 'log_shas', new=fake_log)
    await stask.sign(context, filename, [format])


# build_filelist_dict {{{1
@pytest.mark.parametrize('formats,raises', ((
    ['gpg'], False,
), (
    ['jar', 'mar', 'gpg'], False,
), (
    ['illegal'], True,
)))
def test_build_filelist_dict(context, task_defn, formats, raises):
    full_path = os.path.join(
        context.config['work_dir'], 'cot', 'VALID_TASK_ID',
        'public/build/firefox-52.0a1.en-US.win64.installer.exe',
    )
    expected = {
        'public/build/firefox-52.0a1.en-US.win64.installer.exe': {
            'full_path': full_path,
            'formats': ['gpg'],
        }
    }
    context.task = task_defn

    # first, the file is missing...
    with pytest.raises(TaskVerificationError):
        stask.build_filelist_dict(context, formats)

    mkdir(os.path.dirname(full_path))
    with open(full_path, "w") as fh:
        fh.write("foo")

    if raises:
        # illegal format
        with pytest.raises(TaskVerificationError):
            stask.build_filelist_dict(context, formats)
    else:
        assert stask.build_filelist_dict(context, formats) == expected
