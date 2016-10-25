import os
import tempfile
import json

import unittest
from unittest.mock import patch

from pushapkscript.utils import mkdir, load_json


class UtilsTest(unittest.TestCase):
    def test_mkdir_does_make_dirs(self):
        with tempfile.TemporaryDirectory() as test_dir:
            end_dir = os.path.join(test_dir, 'dir_in_the_middle', 'leaf_dir')
            mkdir(end_dir)

            middle_dirs = list(os.scandir(test_dir))
            self.assertDirIsUniqueAndNamed(middle_dirs, 'dir_in_the_middle')

            leaf_dirs = list(os.scandir(middle_dirs[0].path))
            self.assertDirIsUniqueAndNamed(leaf_dirs, 'leaf_dir')

    def assertDirIsUniqueAndNamed(self, dirs, name):
        self.assertEqual(len(dirs), 1)
        self.assertTrue(dirs[0].is_dir())
        self.assertTrue(dirs[0].name, name)

    @patch('os.makedirs')
    def test_mkdir_mutes_os_errors(self, makedirs):
        makedirs.side_effect = OSError
        mkdir('/dummy/dir')
        makedirs.assert_called_with('/dummy/dir')

    def test_load_json_from_file(self):
        json_object = {'a_key': 'a_value'}

        with tempfile.TemporaryDirectory() as output_dir:
            output_file = os.path.join(output_dir, 'file.json')
            with open(output_file, 'w') as f:
                json.dump(json_object, f)

            self.assertEqual(load_json(output_file), json_object)
