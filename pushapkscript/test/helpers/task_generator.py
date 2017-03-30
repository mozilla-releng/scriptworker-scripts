import os
import json


class TaskGenerator(object):
    def __init__(self):
        self.arm_task_id = 'fwk3elTDSe6FLoqg14piWg'
        self.x86_task_id = 'PKP2v4y0RdqOuLCqhevD2A'

    def generate_file(self, work_dir):
        task_file = os.path.join(work_dir, 'task.json')
        with open(task_file, 'w') as f:
            json.dump(self.generate_json(), f)
        return task_file

    def generate_json(self):
        return json.loads('''{{
          "provisionerId": "some-provisioner-id",
          "workerType": "some-worker-type",
          "schedulerId": "some-scheduler-id",
          "taskGroupId": "some-task-group-id",
          "routes": [],
          "retries": 5,
          "created": "2015-05-08T16:15:58.903Z",
          "deadline": "2015-05-08T18:15:59.010Z",
          "expires": "2016-05-08T18:15:59.010Z",
          "dependencies": ["{}", "{}"],
          "scopes": ["project:releng:googleplay:aurora"],
          "payload": {{
            "upstreamArtifacts": [{{
              "paths": ["public/build/target.apk"],
              "taskId": "fwk3elTDSe6FLoqg14piWg",
              "taskType": "signing"
            }}, {{
              "paths": ["public/build/target.apk"],
              "taskId": "PKP2v4y0RdqOuLCqhevD2A",
              "taskType": "signing"
            }}],
            "google_play_track": "alpha"
          }}
        }}'''.format(self.arm_task_id, self.x86_task_id))
