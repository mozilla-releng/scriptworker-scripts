import json
import os
import tempfile

from unittest.mock import patch

from signingscript.utils import get_detached_signatures, mkdir, load_json


def test_detached_signatures():
    assert get_detached_signatures(["mar", "gpg", "pgp"]) == [("gpg", ".asc", "text/plain")]


def test_mkdir_does_make_dirs():
    with tempfile.TemporaryDirectory() as test_dir:
        end_dir = os.path.join(test_dir, 'dir_in_the_middle', 'leaf_dir')
        mkdir(end_dir)

        middle_dirs = list(os.scandir(test_dir))
        assertDirIsUniqueAndNamed(middle_dirs, 'dir_in_the_middle')

        leaf_dirs = list(os.scandir(middle_dirs[0].path))
        assertDirIsUniqueAndNamed(leaf_dirs, 'leaf_dir')


def assertDirIsUniqueAndNamed(dirs, name):
    assert len(dirs) == 1
    assert dirs[0].is_dir()
    assert dirs[0].name == name


@patch('os.makedirs')
def test_mkdir_mutes_os_errors(makedirs):
    makedirs.side_effect = OSError
    mkdir('/dummy/dir')
    makedirs.assert_called_with('/dummy/dir')


def test_load_json_from_file():
    json_object = {'a_key': 'a_value'}

    with tempfile.TemporaryDirectory() as output_dir:
        output_file = os.path.join(output_dir, 'file.json')
        with open(output_file, 'w') as f:
            json.dump(json_object, f)

        assert load_json(output_file) == json_object
