import logging

import unittest
from unittest.mock import MagicMock, patch

from pushapkscript.script import craft_logging_config, get_default_config


class ScriptTest(unittest.TestCase):
    def test_craft_logging_config(self):
        context = MagicMock()
        context.config = {'verbose': True}

        self.assertEqual(craft_logging_config(context), {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'level': logging.DEBUG
        })

        context.config = {'verbose': False}
        self.assertEqual(craft_logging_config(context), {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'level': logging.INFO
        })

    @patch('os.getcwd')
    def test_get_default_config(self, current_working_dir_patch):
        current_working_dir_patch.return_value = '/a/current/dir'

        self.assertEqual(get_default_config(), {
            'work_dir': '/a/current/work_dir',
            'schema_file': '/a/current/dir/pushapkscript/data/pushapk_task_schema.json',
            'verbose': False,
        })
