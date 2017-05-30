import aiohttp
from contextlib import contextmanager
import os
import pytest

from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException

from signingscript.exceptions import FailedSubprocess, SigningServerError, TaskVerificationError
from signingscript.script import get_default_config
from signingscript.utils import load_signing_server_config, mkdir, SigningServer
import signingscript.task as stask
import signingscript.utils as utils
from signingscript.test import noop_async, noop_sync, tmpdir

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


# sign_file {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize('signtool,format', ((
    'signtool', 'gpg'
), (
    ['signtool'], 'gpg'
)))
async def test_sign_file(context, mocker, format, signtool):
    work_dir = context.config['work_dir']
    path = os.path.join(work_dir, 'filename')

    async def test_cmdln(command):
        assert command == [
            'signtool', "-v",
            "-n", os.path.join(work_dir, "nonce"),
            "-t", os.path.join(work_dir, "token"),
            "-c", context.config['ssl_cert'],
            "-H", "127.0.0.1:9110",
            "-f", format,
            "-o", path, path,
        ]

    context.config['signtool'] = signtool
    mocker.patch.object(stask, '_execute_post_signing_steps', new=noop_async)
    mocker.patch.object(utils, '_execute_subprocess', new=test_cmdln)
    await stask.sign_file(context, path, TEST_CERT_TYPE, [format], context.config['ssl_cert'])


# _execute_pre_signing_steps {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize('filename,expected', ((
    'foo.dmg', 'foo.tar.gz',
), (
    'bar.zip', 'bar.zip',
)))
async def test_execute_pre_signing_steps(context, mocker, filename, expected):
    mocker.patch.object(stask, '_convert_dmg_to_tar_gz', new=noop_async)
    assert await stask._execute_pre_signing_steps(context, filename) == expected


# _execute_post_signing_steps {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize('suffix', ('apk', 'zip'))
async def test_execute_post_signing_steps(context, monkeypatch, suffix):
    work_dir = context.config['work_dir']
    abs_to = os.path.join(work_dir, 'target.{}'.format(suffix))

    async def zip_align_apk_mock(_context, _abs_to):
        if suffix != 'apk':
            assert False  # We shouldn't call this on non-apk
        assert context == _context
        assert abs_to == _abs_to

    def get_hash_mock(_abs_to, hash_type):
        assert abs_to == _abs_to
        assert hash_type in ('sha512', 'sha1')

    monkeypatch.setattr('signingscript.task._zip_align_apk', zip_align_apk_mock)
    monkeypatch.setattr('signingscript.utils.get_hash', get_hash_mock)

    await stask._execute_post_signing_steps(context, 'target.{}'.format(suffix))


# _zip_align_apk {{{1
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

    monkeypatch.setattr('signingscript.utils._execute_subprocess', execute_subprocess_mock)
    monkeypatch.setattr('shutil.move', shutil_mock)

    await stask._zip_align_apk(context, abs_to)


# _convert_dmg_to_tar_gz {{{1
@pytest.mark.asyncio
async def test_convert_dmg_to_tar_gz(context, monkeypatch):
    dmg_path = 'path/to/foo.dmg'
    abs_dmg_path = os.path.join(context.config['work_dir'], dmg_path)
    tarball_path = 'path/to/foo.tar.gz'
    abs_tarball_path = os.path.join(context.config['work_dir'], tarball_path)

    async def execute_subprocess_mock(command, **kwargs):
        assert command in (
            ['dmg', 'extract', abs_dmg_path, 'tmp.hfs'],
            ['hfsplus', 'tmp.hfs', 'extractall', '/', 'tmpdir/app'],
            ['tar', 'czvf', abs_tarball_path, '.'],
        )

    @contextmanager
    def fake_tmpdir():
        yield "tmpdir"

    monkeypatch.setattr('signingscript.utils._execute_subprocess', execute_subprocess_mock)
    monkeypatch.setattr('tempfile.TemporaryDirectory', fake_tmpdir)

    await stask._convert_dmg_to_tar_gz(context, dmg_path)


# detached_sigfiles {{{1
@pytest.mark.parametrize('formats,expected', ((
    ['mar', 'jar', 'emevoucher'], []
), (
    ['mar', 'jar', 'gpg'], ['foo.asc']
), (
    ['gpg'], ['foo.asc']
)))
def test_detached_sigfiles(formats, expected):
    assert stask.detached_sigfiles("foo", formats) == expected


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
