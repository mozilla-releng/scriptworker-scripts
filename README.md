# Funsize Balrogworker

## Installation

```bash
make update_pubkeys
make build
make start
```

Note, currently scriptworker is installed from the head of the 
[github repo](https://github.com/escapewindow/scriptworker). 

## Configuration
In the dockerfile, the following environment variables need to be set:
(They can be found in the sample_Dockerfile)

- TASKCLUSTER_CLIENT_ID
- TASKCLUSTER_ACCESS_TOKEN
- SCRIPTWORKER_WORKER_ID
- BALROG_API_ROOT
- BALROG_USERNAME
- BALROG_PASSWORD
- S3_BUCKET
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY     

## Deployment

TODO. Will be deployed via [CloudOps Dockerflow](https://github.com/mozilla-services/Dockerflow/)

## Creating Tasks

The task schema that the program expects is: 

```json
"payload": {
    "parent_task_artifacts_url": "https://queue.taskcluster.net/v1/task/<taskID>/artifacts/public/env",
    "signing_cert": ("nightly","release","dep")
}
```
