import json
import copy
from signingscript.script import get_default_config
from signingscript.task import validate_task_schema
from scriptworker.context import Context

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
  "dependencies": ["VALID_TASK_ID"],
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


def test_validate_task():
    context = Context()
    context.task = valid_task
    context.config = get_default_config()
    validate_task_schema(context)
