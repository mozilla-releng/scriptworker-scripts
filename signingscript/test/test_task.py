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
    "apks": {
      "armv7_v15": "https://queue.taskcluster.net/v1/task/DIYnEVJ_SaSLGWtd3_n3VA/artifacts/public%2Fbuild%2Ffennec-46.0a2.en-US.android-arm.apk",
      "x86": "https://queue.taskcluster.net/v1/task/EZJ0suL7St65V_MM0iBhKw/artifacts/public%2Fbuild%2Ffennec-46.0a2.en-US.android-i386.apk"
    },
    "google_play_track": "alpha"
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
