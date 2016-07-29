# Funsize Balrogworker

A small scriptworker used for submitting [funsize](https://wiki.mozilla.org/ReleaseEngineering/Funsize) metadata to [balrog](https://wiki.mozilla.org/Balrog).


## Installation

The application is dockerized and can be built and run with the following
commands. Or just pull latest from dockerhub at mozilla/balrogworker.  

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
(Optional):
- S3_BUCKET
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY     

If any of the S3 credentials are missing, balrogworker will skip uploads
and pass through the taskcluster artifact url directly to balrog. This 
can also be manually forced via the `--disable-s3` flag. Note that you 
may need to whitelist taskcluster's domain name on your installation of 
balrog. 

## Deployment

TODO. Will be deployed via [CloudOps Dockerflow](https://github.com/mozilla-services/Dockerflow/)
For now, you can run it locally:

```bash
docker run -ti \
    --name balrogworker \
-e TASKCLUSTER_CLIENT_ID="tc-client-id" \
-e TASKCLUSTER_ACCESS_TOKEN="tc-access-token" \
-e SCRIPTWORKER_WORKER_ID="dummy-worker-yourname1" \
-e BALROG_API_ROOT="balrog" \
-e BALROG_USERNAME="balrogadmin" \
-e BALROG_PASSWORD="wootwoot" \
-e S3_BUCKET="bucket-name" \
-e AWS_ACCESS_KEY_ID="key-id" \
-e AWS_SECRET_ACCESS_KEY="key-secret" \
mozilla/balrogworker
```

## Testing

Tests are run on taskcluster, and are triggered by pull requests or any
branch activity. 

## Creating Tasks

The task schema that the program expects is: 

```json
"payload": {
    "parent_task_artifacts_url": "https://queue.taskcluster.net/v1/task/<taskID>/artifacts/public/env",
    "signing_cert": ["nightly","release","dep"] (Pick one)
}
```

If testing locally, make sure that the `worker_type` in the
task definition is the same as the one declared in `config.json`
