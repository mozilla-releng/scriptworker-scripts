import json
import mock
import os
import pytest

from treescript.test import tmpdir
import treescript.utils as utils
from treescript.exceptions import TaskVerificationError, FailedSubprocess


assert tmpdir  # silence flake8

TEST_ACTION_TAG = 'project:releng:treescript:action:tagging'
TEST_ACTION_BUMP = 'project:releng:treescript:action:versionbump'
TEST_ACTION_INVALID = 'project:releng:treescript:action:invalid'


# mkdir {{{1
def test_mkdir_does_make_dirs(tmpdir):

    def assertDirIsUniqueAndNamed(dirs, name):
        assert len(dirs) == 1
        assert dirs[0].is_dir()
        assert dirs[0].name == name

    end_dir = os.path.join(tmpdir, 'dir_in_the_middle', 'leaf_dir')
    utils.mkdir(end_dir)

    middle_dirs = list(os.scandir(tmpdir))
    assertDirIsUniqueAndNamed(middle_dirs, 'dir_in_the_middle')

    leaf_dirs = list(os.scandir(middle_dirs[0].path))
    assertDirIsUniqueAndNamed(leaf_dirs, 'leaf_dir')


def test_mkdir_mutes_os_errors(mocker):
    m = mocker.patch.object(os, 'makedirs')
    m.side_effect = OSError
    utils.mkdir('/dummy/dir')
    m.assert_called_with('/dummy/dir')


# load_json {{{1
def test_load_json_from_file(tmpdir):
    json_object = {'a_key': 'a_value'}

    output_file = os.path.join(tmpdir, 'file.json')
    with open(output_file, 'w') as f:
        json.dump(json_object, f)

    assert utils.load_json(output_file) == json_object


# task_task_action_types {{{1
@pytest.mark.parametrize(
    'scopes', ([TEST_ACTION_TAG], [TEST_ACTION_BUMP], [TEST_ACTION_TAG, TEST_ACTION_BUMP])
)
def test_task_action_types_valid_scopes(scopes):
    task = {"scopes": scopes}
    assert tuple(scopes) == utils.task_action_types(task)


@pytest.mark.parametrize(
    'scopes', ([TEST_ACTION_INVALID], [TEST_ACTION_TAG, TEST_ACTION_INVALID])
)
def test_task_action_types_invalid_action(scopes):
    task = {"scopes": scopes}
    with pytest.raises(TaskVerificationError):
        utils.task_action_types(task)


@pytest.mark.parametrize(
    'scopes', ([], ["project:releng:foo:not:for:here"])
)
def test_task_action_types_missing_action(scopes):
    task = {"scopes": scopes}
    with pytest.raises(TaskVerificationError):
        utils.task_action_types(task)


# log_output {{{1
@pytest.mark.asyncio
async def test_log_output(tmpdir, mocker):
    logged = []
    with open(__file__, 'r') as fh:
        contents = fh.read()

    def info(msg):
        logged.append(msg)

    class AsyncIterator:
        def __init__(self):
            # .split('\n') can cause this to fail due to blank lines in file.
            # which will cause the logger to think it hit EOF.
            self.contents = contents.splitlines(keepends=True)

        async def __aiter__(self):
            return self

        async def __anext__(self):
            while self.contents:
                return self.contents.pop(0).encode('utf-8')

    mocklog = mocker.patch.object(utils, 'log')
    mocklog.info = info
    mockfh = mock.MagicMock()
    aiter = AsyncIterator()
    mockfh.readline = aiter.__anext__
    await utils.log_output(mockfh)
    assert contents.rstrip() == '\n'.join(logged)


# execute_subprocess {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize('exit_code', (1, 0))
async def test_execute_subprocess(exit_code):
    command = ['bash', '-c', 'echo "hi"; exit  {}'.format(exit_code)]
    if exit_code != 0:
        with pytest.raises(FailedSubprocess):
            await utils.execute_subprocess(command)
    else:
        await utils.execute_subprocess(command, cwd="/tmp")
