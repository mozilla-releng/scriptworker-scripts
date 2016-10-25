import logging

import unittest
from unittest.mock import MagicMock

from pushapkscript.script import craft_logging_config


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
