from unittest import TestCase
from signingworker.task import task_signing_formats, task_cert_type
from signingworker.exceptions import TaskVerificationError


class TestTaskSigningFormats(TestCase):
    def test_task_signing_formats(self):
        task = {"scopes": ["signing:cert:dep", "signing:format:mar",
                           "signing:format:gpg"]}
        self.assertEqual(["mar", "gpg"], task_signing_formats(task))


class TestTaskCertType(TestCase):
    def test_task_cert_type(self):
        task = {"scopes": ["signing:cert:dep", "signing:type:mar",
                           "signing:type:gpg"]}
        self.assertEqual("signing:cert:dep", task_cert_type(task))

    def test_task_cert_type_error(self):
        task = {"scopes": ["signing:cert:dep", "signing:cert:notdep",
                           "signing:type:gpg"]}
        self.assertRaises(TaskVerificationError, task_cert_type, task)
