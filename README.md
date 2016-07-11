# Funsize Balrogworker

## Installation

```bash
make update_pubkeys
make build
make start
```

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
