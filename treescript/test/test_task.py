import os
import pytest

from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException

from treescript.script import get_default_config
import treescript.task as stask
from treescript.test import tmpdir

assert tmpdir  # silence flake8


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
    context.config['work_dir'] = os.path.join(tmpdir, 'work')
    yield context


# validate_task_schema {{{1
def test_missing_mandatory_urls_are_reported(context, task_defn):
    context.task = task_defn
    del(context.task['scopes'])

    with pytest.raises(ScriptWorkerTaskException):
        stask.validate_task_schema(context)


def test_no_error_is_reported_when_no_missing_url(context, task_defn):
    context.task = task_defn
    stask.validate_task_schema(context)
