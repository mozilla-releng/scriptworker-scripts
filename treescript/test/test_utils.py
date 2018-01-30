import json
# import mock
import os
import pytest

from treescript.test import tmpdir
import treescript.utils as utils
from treescript.exceptions import TaskVerificationError


assert tmpdir  # silence flake8

TEST_ACTION_TAG = 'project:releng:treescript:action:tagging'
TEST_ACTION_BUMP = 'project:releng:treescript:action:versionbump'


# load_json {{{1
def test_load_json_from_file(tmpdir):
    json_object = {'a_key': 'a_value'}

    output_file = os.path.join(tmpdir, 'file.json')
    with open(output_file, 'w') as f:
        json.dump(json_object, f)

    assert utils.load_json(output_file) == json_object


# task_task_action_types {{{1
def test_task_action_types_only_one():
    task = {"scopes": [TEST_ACTION_TAG,
                       "project:releng:signing:type:mar",
                       "project:releng:signing:type:gpg"]}
    assert (TEST_ACTION_TAG,) == utils.task_action_types(task)


def test_task_action_types_missing_action():
    task = {"scopes": ["project:releng:signing:cert:notdep",
                       "project:releng:signing:type:gpg"]}
    with pytest.raises(TaskVerificationError):
        utils.task_action_types(task)
