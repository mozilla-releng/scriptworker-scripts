import aiohttp
import os
import pytest

from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException

from signingscript.exceptions import SigningServerError
from signingscript.script import get_default_config
from signingscript.utils import load_signing_server_config, SigningServer
import signingscript.task as stask
from signingscript.test import event_loop, noop_sync, tmpdir

assert event_loop or tmpdir  # silence flake8


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


# task_cert_type {{{1
def test_task_cert_type():
    task = {"scopes": [TEST_CERT_TYPE,
                       "project:releng:signing:type:mar",
                       "project:releng:signing:type:gpg"]}
    assert TEST_CERT_TYPE == stask.task_cert_type(task)


def test_task_cert_type_error():
    task = {"scopes": [TEST_CERT_TYPE,
                       "project:releng:signing:cert:notdep",
                       "project:releng:signing:type:gpg"]}
    with pytest.raises(ScriptWorkerTaskException):
        stask.task_cert_type(task)


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


# get_suitable_signing_servers {{{1
@pytest.mark.parametrize('formats,expected', ((
    ['gpg'], [["127.0.0.1:9110", "user", "pass", ["gpg"]]]
), (
    ['invalid'], []
)))
def test_get_suitable_signing_servers(context, formats, expected):
    expected_servers = []
    for info in expected:
        expected_servers.append(
            SigningServer(*info)
        )

    assert stask.get_suitable_signing_servers(
        context.signing_servers, TEST_CERT_TYPE,
        formats
    ) == expected_servers


# get_token {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize('exc,contents', ((
    ScriptWorkerTaskException, 'token'
), (
    None, ''
), (
    None, 'token'
)))
async def test_get_token(event_loop, mocker, tmpdir, exc, contents, context):

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


# zipalign {{{1
@pytest.mark.asyncio
async def test_execute_post_signing_steps(context, monkeypatch):
    work_dir = context.config['work_dir']
    abs_to = os.path.join(work_dir, 'target.apk')

    async def zip_align_apk_mock(_context, _abs_to):
        assert context == _context
        assert abs_to == _abs_to

    def get_hash_mock(_abs_to, hash_type):
        assert abs_to == _abs_to
        assert hash_type in ('sha512', 'sha1')

    monkeypatch.setattr('signingscript.task._zip_align_apk', zip_align_apk_mock)
    monkeypatch.setattr('signingscript.utils.get_hash', get_hash_mock)

    await stask._execute_post_signing_steps(context, 'target.apk')


@pytest.mark.asyncio
@pytest.mark.parametrize('is_verbose', (True, False))
async def test_zip_align_apk(context, monkeypatch, is_verbose):
    context.config['zipalign'] = '/path/to/android/sdk/zipalign'
    context.config['verbose'] = is_verbose
    abs_to = '/absolute/path/to/apk.apk'

    async def execute_subprocess_mock(command):
        if is_verbose:
            assert command[0:4] == ['/path/to/android/sdk/zipalign', '-v', '4', abs_to]
            assert len(command) == 5
        else:
            assert command[0:3] == ['/path/to/android/sdk/zipalign', '4', abs_to]
            assert len(command) == 4

    def shutil_mock(_, destination):
        assert destination == abs_to

    monkeypatch.setattr('signingscript.task._execute_subprocess', execute_subprocess_mock)
    monkeypatch.setattr('shutil.move', shutil_mock)

    await stask._zip_align_apk(context, abs_to)
