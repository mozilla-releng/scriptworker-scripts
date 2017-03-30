import unittest

from pushapkscript.script import get_default_config
from pushapkscript.task import validate_task_schema, extract_channel
from pushapkscript.exceptions import TaskVerificationError

from scriptworker.context import Context

from pushapkscript.test.helpers.task_generator import TaskGenerator


class TaskTest(unittest.TestCase):
    def setUp(self):
        self.context = Context()
        self.context.config = get_default_config()

    def test_validate_task(self):
        self.context.task = TaskGenerator().generate_json()
        validate_task_schema(self.context)

    def test_extract_supported_channels(self):
        data = ({
            'task': {'scopes': ['project:releng:googleplay:aurora']},
            'expected': 'aurora'
        }, {
            'task': {'scopes': ['project:releng:googleplay:beta']},
            'expected': 'beta'
        }, {
            'task': {'scopes': ['project:releng:googleplay:release']},
            'expected': 'release'
        })

        for item in data:
            self.assertEqual(extract_channel(item['task']), item['expected'])

    def test_extract_channel_fails_when_too_many_channels_are_given(self):
        with self.assertRaises(TaskVerificationError):
            extract_channel({
                'scopes': ['project:releng:googleplay:beta', 'project:releng:googleplay:release']
            })

    def test_extract_channel_fails_when_given_unsupported_channel(self):
        with self.assertRaises(TaskVerificationError):
            extract_channel({
                'scopes': ['project:releng:googleplay:unexistingchannel']
            })
