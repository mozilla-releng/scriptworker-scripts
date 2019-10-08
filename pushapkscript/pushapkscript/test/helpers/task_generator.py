class TaskGenerator(object):
    def __init__(self, rollout_percentage=None, should_commit_transaction=False):
        self.arm_task_id = 'fwk3elTDSe6FLoqg14piWg'
        self.x86_task_id = 'PKP2v4y0RdqOuLCqhevD2A'
        self.should_commit_transaction = should_commit_transaction
        self.rollout_percentage = rollout_percentage

    def generate_task(self, product_name, channel=None):
        arm_task_id = self.arm_task_id
        x86_task_id = self.x86_task_id
        task = {
          "provisionerId": "some-provisioner-id",
          "workerType": "some-worker-type",
          "schedulerId": "some-scheduler-id",
          "taskGroupId": "some-task-group-id",
          "routes": [],
          "retries": 5,
          "created": "2015-05-08T16:15:58.903Z",
          "deadline": "2015-05-08T18:15:59.010Z",
          "expires": "2016-05-08T18:15:59.010Z",
          "dependencies": [arm_task_id, x86_task_id],
          "scopes": ["project:releng:googleplay:{}".format(product_name)],
          "payload": {
            "upstreamArtifacts": [{
              "paths": ["public/build/target.apk"],
              "taskId": arm_task_id,
              "taskType": "signing",
            }, {
              "paths": ["public/build/target.apk"],
              "taskId": x86_task_id,
              "taskType": "signing",
            }],
          },
        }

        if channel:
            task['payload']['channel'] = channel

        if self.rollout_percentage:
            task['payload']['rollout_percentage'] = self.rollout_percentage

        if self.should_commit_transaction:
            task['payload']['commit'] = True

        return task
