import os
import pytest

from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException

from treescript.exceptions import TaskVerificationError
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
        'scopes': ['tagging'],
        'payload': {
          'upstreamArtifacts': [{
            'taskType': 'build',
            'taskId': 'VALID_TASK_ID',
            'formats': ['gpg'],
            'paths': ['public/build/firefox-52.0a1.en-US.win64.installer.exe'],
          }]
        },
        "metadata": {
            "source": "https://hg.mozilla.org/releases/mozilla-test-source"
                      "/file/1b4ab9a276ce7bb217c02b83057586e7946860f9/taskcluster/ci/foobar",
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


@pytest.mark.parametrize('tag_info', (
    {'revision', 'foobar'},
    {'tags': 'some_string'},
    {'tags': ['some_string']},
    {'tags': 'somestring', 'revision': 'foobar'},
    {'tags': [], 'revision': 'foobar'},
    {'tags': [1], 'revision': 'foobar'},
    {'tags': ['tag', -1], 'revision': 'foobar'},
    {'tags': ['mercury'], 'revision': 6}
))
def test_tag_info_invalid(context, task_defn, tag_info):
    context.task = task_defn
    context.task['payload']['tag_info'] = tag_info
    with pytest.raises(ScriptWorkerTaskException):
        stask.validate_task_schema(context)


def test_no_error_is_reported_when_no_missing_url(context, task_defn):
    context.task = task_defn
    stask.validate_task_schema(context)


@pytest.mark.parametrize('source_url,raises', ((
        "https://bitbucket.org/mozilla/mozilla-central/file/foobar", TaskVerificationError
    ), (
        "http://hg.mozilla.org/releases/mozilla-test-source/file/default/taskcluster/ci/foobar",
        TaskVerificationError
    ), (
        "https://hg.mozilla.org/releases/mozilla-test-source/raw-file/default/taskcluster/ci/foobar",
        TaskVerificationError
)))
def test_get_source_repo_raises(task_defn, source_url, raises):
    task_defn['metadata']['source'] = source_url
    with pytest.raises(raises):
        stask.get_source_repo(task_defn)


@pytest.mark.parametrize('source_repo', (
    "https://hg.mozilla.org/mozilla-central",
    "https://hg.mozilla.org/releases/mozilla-release",
    "https://hg.mozilla.org/releases/mozilla-esr120",
    "https://hg.mozilla.org/projects/mozilla-test-bed"
))
def test_get_source_repo(task_defn, source_repo):
    task_defn['metadata']['source'] = "{}/file/default/taskcluster/ci/foobar".format(source_repo)
    assert source_repo == stask.get_source_repo(task_defn)


def test_get_source_repo_no_source(task_defn):
    del task_defn['metadata']['source']
    with pytest.raises(TaskVerificationError):
        stask.get_source_repo(task_defn)
    del task_defn['metadata']
    with pytest.raises(TaskVerificationError):
        stask.get_source_repo(task_defn)


@pytest.mark.parametrize('tag_info', (
    {'revision': 'deadbeef', 'tags': ['FIREFOX_54.0b3_RELEASE', 'BOB']},
    {'revision': 'beef0001', 'tags': ['FIREFOX_59.0b3_RELEASE', 'FRED']}
))
def test_tag_info(task_defn, tag_info):
    task_defn['payload']['tag_info'] = tag_info
    tested_info = stask.get_tag_info(task_defn)
    assert tested_info == tag_info


def test_tag_missing_tag_info(task_defn):
    with pytest.raises(TaskVerificationError):
        stask.get_tag_info(task_defn)


@pytest.mark.parametrize('bump_info', (
    {'next_version': '1.2.4', 'files': ['browser/config/version.txt']},
    {'next_version': '98.0.1b3', 'files': ['config/milestone.txt', 'browser/config/version_display.txt']}
))
def test_bump_info(task_defn, bump_info):
    task_defn['payload']['version_bump_info'] = bump_info
    tested_info = stask.get_version_bump_info(task_defn)
    assert tested_info == bump_info


def test_bump_missing_bump_info(task_defn):
    with pytest.raises(TaskVerificationError):
        stask.get_version_bump_info(task_defn)
