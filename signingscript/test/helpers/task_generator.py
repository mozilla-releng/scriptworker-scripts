import os
import json


class TaskGenerator(object):
    def __init__(self, urls=None):
        self.urls = urls if urls is not None else [
            'https://queue.taskcluster.net/v1/task/ZB9X1cvCRo-hTps7BDk8pw/artifacts/\
public%2Fbuild%2Ffirefox-52.0a1.en-US.win64.installer.exe'
        ]

    def generate_file(self, work_dir):
        task_file = os.path.join(work_dir, 'task.json')
        with open(task_file, 'w') as f:
            json.dump(self.generate_json(), f)
        return task_file

    def generate(self):
        return {
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
              "unsignedArtifacts": self.urls
            }
        }
