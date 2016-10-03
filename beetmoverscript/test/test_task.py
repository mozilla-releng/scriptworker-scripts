import json
from scriptworker.context import Context
from beetmoverscript.task import validate_task_schema
from beetmoverscript.utils import load_json


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
    "version": "99.0a1",
    "upload_date": 1472747174,
    "taskid_to_beetmove": "VALID_TASK_ID",
    "template_key": "some_template_key"
  }
}
""")


def get_default_config():
    return load_json(path="beetmoverscript/test/test_config_example.json")


def test_validate_task():
    context = Context()
    context.task = valid_task
    context.config = get_default_config()
    validate_task_schema(context)
