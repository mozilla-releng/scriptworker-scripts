import os

import pytest

from addonscript.test import tmpdir
from scriptworker.context import Context
from scriptworker.exceptions import TaskVerificationError

import addonscript.task as task

assert tmpdir  # silence flake8


@pytest.fixture(scope='function')
async def context(tmpdir):
    context = Context()
    context.config = {
        'jwt_user': 'test-user',
        'jwt_secret': 'secret',
        'work_dir': tmpdir,
    }
    return context


@pytest.fixture(scope='function',
                params=(
                    ('unlisted', ('en-US', 'en-GB')),
                    ('listed', ('de', 'ja', 'ja-JP-mac'))
                ),
                ids=('unlisted', 'listed'))
async def task_dfn(request):
    channel, locales = request.param
    payload = {
        'channel': channel,
        'upstreamArtifacts': []
    }
    i = 0
    for locale in locales:
        i += 1
        payload['upstreamArtifacts'].append({
            "paths": [
              "public/build/{}/target.langpack.xpi".format(locale)
            ],
            "taskId": "UPSTREAM{}".format(i),
            "taskType": "build"
        })
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
        'dependencies': ['UPSTREAM{}'.format(n + 1) for n in range(i)],
        'scopes': [],
        'payload': payload,
        "metadata": {
            "source": "https://hg.mozilla.org/releases/mozilla-test-source"
                      "/file/1b4ab9a276ce7bb217c02b83057586e7946860f9/taskcluster/ci/foobar",
        }
    }


def test_get_channel(task_dfn):
    channel = task_dfn['payload']['channel']
    assert channel == task.get_channel(task_dfn)


def test_get_channel_missing(task_dfn):
    del task_dfn['payload']['channel']
    with pytest.raises(TaskVerificationError):
        task.get_channel(task_dfn)


def test_build_filelist(context, task_dfn):
    expected_paths = set()
    for a in task_dfn['payload']['upstreamArtifacts']:
        abs_path = os.path.join(context.config['work_dir'], 'cot', a['taskId'], a['paths'][0])
        expected_paths.add(abs_path)
        os.makedirs(os.path.dirname(abs_path))
        with open(abs_path, 'w') as f:
            # Make file exist
            print('something', file=f)
    context.task = task_dfn
    file_list = task.build_filelist(context)
    assert len(file_list) == len(task_dfn['payload']['upstreamArtifacts'])
    assert expected_paths == set(file_list)
    assert isinstance(file_list, type([]))


def test_build_filelist_missing_file(context, task_dfn):
    expected_paths = set()
    for a in task_dfn['payload']['upstreamArtifacts']:
        abs_path = os.path.join(context.config['work_dir'], 'cot', a['taskId'], a['paths'][0])
        expected_paths.add(abs_path)
        os.makedirs(os.path.dirname(abs_path))
        with open(abs_path, 'w') as f:
            # Make file exist
            print('something', file=f)
    task_dfn['payload']['upstreamArtifacts'][-1]['taskId'] = "MISSINGTASK"
    context.task = task_dfn
    with pytest.raises(TaskVerificationError):
        task.build_filelist(context)
