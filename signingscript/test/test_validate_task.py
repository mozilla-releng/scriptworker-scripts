from unittest import TestCase
import json
import copy

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
    "unsignedArtifacts": [
      "url"
    ]
  }
}
""")

no_scopes = copy.deepcopy(valid_task)
no_scopes["scopes"] = []


class TestValidateTask(TestCase):
    pass
