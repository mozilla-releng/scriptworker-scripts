#!/bin/bash

: "${TASKCLUSTER_CLIENT_ID:?Need to set TASKCLUSTER_CLIENT_ID}"
: "${TASKCLUSTER_ACCESS_TOKEN:?Need to set TASKCLUSTER_ACCESS_TOKEN}"
: "${SCRIPTWORKER_WORKER_ID:?Need to set SCRIPTWORKER_WORKER_ID}"
: "${BALROG_API_ROOT:?Need to set BALROG_API_ROOT}"
: "${BALROG_USERNAME:?Need to set BALROG_USERNAME}"
: "${BALROG_PASSWORD:?Need to set BALROG_PASSWORD}"
# Do not require S3 creds as they're not mandatory

/app/py3.5/bin/scriptworker /app/config.json