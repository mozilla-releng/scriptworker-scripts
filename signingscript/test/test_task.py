import os
import pytest

from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException

from signingscript.script import get_default_config
from signingscript.task import task_signing_formats, task_cert_type, validate_task_schema, \
    _zip_align_apk, _execute_post_signing_steps

from signingscript.test.helpers import task_generator


def test_task_signing_formats():
    task = {"scopes": ["project:releng:signing:cert:dep-signing",
                       "project:releng:signing:format:mar",
                       "project:releng:signing:format:gpg"]}
    assert ["mar", "gpg"] == task_signing_formats(task)


def test_task_cert_type():
    task = {"scopes": ["project:releng:signing:cert:dep-signing",
                       "project:releng:signing:type:mar",
                       "project:releng:signing:type:gpg"]}
    assert "project:releng:signing:cert:dep-signing" == task_cert_type(task)


def test_task_cert_type_error():
    task = {"scopes": ["project:releng:signing:cert:dep-signing",
                       "project:releng:signing:cert:notdep",
                       "project:releng:signing:type:gpg"]}
    with pytest.raises(ScriptWorkerTaskException):
        task_cert_type(task)


@pytest.fixture
def context():
    context = Context()
    context.config = get_default_config()
    return context


def test_missing_mandatory_urls_are_reported(context):
    context.task = task_generator.generate_object()
    del(context.task['scopes'])

    with pytest.raises(ScriptWorkerTaskException):
        validate_task_schema(context)


def test_no_error_is_reported_when_no_missing_url(context):
    context.task = task_generator.generate_object()
    validate_task_schema(context)


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

    await _execute_post_signing_steps(context, 'target.apk')


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

    async def shutil_mock(_, destination):
        assert destination == abs_to

    monkeypatch.setattr('signingscript.task._execute_subprocess', execute_subprocess_mock)
    monkeypatch.setattr('shutil.move', shutil_mock)

    await _zip_align_apk(context, abs_to)
