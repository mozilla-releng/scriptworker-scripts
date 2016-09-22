import unittest

from signingscript.script import get_default_config
from signingscript.task import validate_task_schema

from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException

from signingscript.test.helpers.task_generator import TaskGenerator


class TaskTest(unittest.TestCase):
    def setUp(self):
        self.context = Context()
        self.context.config = get_default_config()

    def test_validate_task(self):
        self.context.task = TaskGenerator().generate_json()
        validate_task_schema(self.context)

    def test_missing_mandatory_apks_are_reported(self):
        self.context.task = TaskGenerator(
            apks={'armv7_v15': ''}  # x86 is missing, for instance
        ).generate_json()

        with self.assertRaises(ScriptWorkerTaskException):
            validate_task_schema(self.context)

    def test_no_error_is_reported_when_no_missing_apk(self):
        self.context.task = TaskGenerator(
            apks={'armv7_v15': '', 'x86': ''}
        ).generate_json()

        validate_task_schema(self.context)
