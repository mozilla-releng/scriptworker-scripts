import os
import json


class TaskGenerator(object):
    def __init__(self, google_play_track='alpha', rollout_percentage=None, should_commit_transaction=False):
        self.arm_task_id = 'fwk3elTDSe6FLoqg14piWg'
        self.x86_task_id = 'PKP2v4y0RdqOuLCqhevD2A'
        self.google_play_strings_task_id = 'bgP9T6AnTpyTVsNA7M3OnA'
        self.should_commit_transaction = should_commit_transaction
        self.google_play_track = google_play_track
        self.rollout_percentage = rollout_percentage

    def generate_file(self, work_dir):
        task_file = os.path.join(work_dir, 'task.json')
        with open(task_file, 'w') as f:
            json.dump(self.generate_json(), f)
        return task_file

    def generate_json(self):
        json_content = json.loads('''{{
          "provisionerId": "some-provisioner-id",
          "workerType": "some-worker-type",
          "schedulerId": "some-scheduler-id",
          "taskGroupId": "some-task-group-id",
          "routes": [],
          "retries": 5,
          "created": "2015-05-08T16:15:58.903Z",
          "deadline": "2015-05-08T18:15:59.010Z",
          "expires": "2016-05-08T18:15:59.010Z",
          "dependencies": ["{arm_task_id}", "{x86_task_id}"],
          "scopes": ["project:releng:googleplay:aurora"],
          "payload": {{
            "upstreamArtifacts": [{{
              "paths": ["public/build/target.apk"],
              "taskId": "{arm_task_id}",
              "taskType": "signing"
            }}, {{
              "paths": ["public/build/target.apk"],
              "taskId": "{x86_task_id}",
              "taskType": "signing"
            }}, {{
              "paths": ["public/google_play_strings.json"],
              "taskId": "{strings_task_id}",
              "taskType": "build",
              "optional": true
            }}],
            "google_play_track": "{google_play_track}"
          }}
        }}'''.format(
            arm_task_id=self.arm_task_id,
            x86_task_id=self.x86_task_id,
            strings_task_id=self.google_play_strings_task_id,
            google_play_track=self.google_play_track,
        ))

        if self.rollout_percentage:
            json_content['payload']['rollout_percentage'] = self.rollout_percentage

        if self.should_commit_transaction:
            json_content['payload']['commit'] = True

        return json_content
