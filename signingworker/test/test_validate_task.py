from unittest import TestCase
import json
import copy
from signingworker.task import validate_task
from signingworker.exceptions import TaskVerificationError
from jsonschema.exceptions import ValidationError

valid_task = json.loads("""
{
  "provisionerId": "meh",
  "workerType": "workertype",
  "schedulerId": "task-graph-scheduler",
  "taskGroupId": "some",
  "routes": [],
  "retries": 5,
  "created": "2015-05-08T16:15:58.903Z",
  "deadline": "2015-05-08T18:15:59.010Z",
  "expires": "2016-05-08T18:15:59.010Z",
  "scopes": ["signing"],
  "payload": {
    "signingManifest": "manifest.json"
  }
}
""")

supported_scopes = ["signing"]
no_scopes = copy.deepcopy(valid_task)
no_scopes["scopes"] = []
no_signing_in_scopes = copy.deepcopy(valid_task)
no_signing_in_scopes["scopes"] = ["no-signing"]

class TestValidateTask(TestCase):
    def test_valid_task(self):
        self.assertIsNone(validate_task(valid_task, supported_scopes))

    def test_no_scopes(self):
        self.assertRaises(ValidationError, validate_task, no_scopes,
                          supported_scopes)

    def test_no_signing_in_scopes(self):
        self.assertRaises(TaskVerificationError, validate_task,
                          no_signing_in_scopes, supported_scopes)
