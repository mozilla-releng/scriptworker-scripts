#!/bin/bash
set -o errexit -o pipefail

test_var_set() {
  local varname=$1

  if [[ -z "${!varname}" ]]; then
    echo "error: ${varname} is not set"
    exit 1
  fi
}

test_var_set 'TASKCLUSTER_ROOT_URL'

export VERIFY_CHAIN_OF_TRUST=false

export WORKER_TYPE="${PROJECT_NAME}${WORKER_SUFFIX}"
export WORKER_GROUP=${WORKER_TYPE}
export WORKER_ID_PREFIX="${WORKER_TYPE}-"
