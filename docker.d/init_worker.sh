#!/bin/bash
set -e

case $ENV in
  dev|fake-prod)
    export API_ROOT_V2="http://10.8.9.239"
    export TASKCLUSTER_SCOPE="project:releng:ship-it:server:staging"
    ;;
  prod)
    export API_ROOT_V2="http://shipitapi-prod-shipitapi-app-1"
    export TASKCLUSTER_SCOPE="project:releng:ship-it:server:production"
    ;;
  *)
    exit 1
    ;;
esac

case $COT_PRODUCT in
  firefox)
    export TASKCLUSTER_SCOPE_PREFIX="project:releng:ship-it:"
    ;;
  thunderbird)
    export TASKCLUSTER_SCOPE_PREFIX="project:comm:thunderbird:releng:ship-it:"
    ;;
  *)
    exit 1
    ;;
esac

export MARK_AS_SHIPPED_SCHEMA_FILE="/app/shipitscript/data/mark_as_shipped_task_schema.json"
