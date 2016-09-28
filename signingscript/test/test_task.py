import unittest

from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerTaskException

from signingscript.task import task_signing_formats, task_cert_type, validate_task_schema
from signingscript.script import get_default_config

from signingscript.test.helpers.task_generator import TaskGenerator


class TaskTest(unittest.TestCase):
    def test_task_signing_formats(self):
        task = {"scopes": ["project:releng:signing:cert:dep",
                           "project:releng:signing:format:mar",
                           "project:releng:signing:format:gpg"]}
        self.assertEqual(["mar", "gpg"], task_signing_formats(task))

    def test_task_cert_type(self):
        task = {"scopes": ["project:releng:signing:cert:dep",
                           "project:releng:signing:type:mar",
                           "project:releng:signing:type:gpg"]}
        self.assertEqual("project:releng:signing:cert:dep", task_cert_type(task))

    def test_task_cert_type_error(self):
        task = {"scopes": ["project:releng:signing:cert:dep",
                           "project:releng:signing:cert:notdep",
                           "project:releng:signing:type:gpg"]}
        with self.assertRaises(ScriptWorkerTaskException):
            task_cert_type(task)

    def setUp(self):
        self.context = Context()
        self.context.config = get_default_config()

    def test_missing_mandatory_urls_are_reported(self):
        self.context.task = TaskGenerator(
            urls=[]  # no URLs provided
        ).generate()

        with self.assertRaises(ScriptWorkerTaskException):
            validate_task_schema(self.context)

    def test_no_error_is_reported_when_no_missing_url(self):
        self.context.task = TaskGenerator().generate()
        validate_task_schema(self.context)
