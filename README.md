# Funsize Balrogworker

A small scriptworker used for submitting [funsize](https://wiki.mozilla.org/ReleaseEngineering/Funsize) metadata to [balrog](https://wiki.mozilla.org/Balrog).


## Installation

The application is dockerized and can be built and run with the following
commands. 

```bash
make update_pubkeys
make build
make start
```

Note, currently scriptworker is installed from the head of the 
[github repo](https://github.com/escapewindow/scriptworker). 

## Configuration
At runtime, the following environment variables need to be set:

Scriptworker Specfic:
- TASKCLUSTER_CLIENT_ID
- TASKCLUSTER_ACCESS_TOKEN
- SCRIPTWORKER_WORKER_ID

Balrog Specific:
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
    "signing_cert": ["nightly","release","dep"] # (Pick one)
}
```

If testing locally, make sure that the `worker_type` in the
task definition is the same as the one declared in `config.json`