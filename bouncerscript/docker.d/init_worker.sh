#!/bin/bash
set -o errexit -o pipefail

test_var_set() {
  local varname=$1

  if [[ -z "${!varname}" ]]; then
    echo "error: ${varname} is not set"
    exit 1
  fi
}

#
# Check that all required variables exist
#
test_var_set 'COT_PRODUCT'
test_var_set 'PROJECT_NAME'
test_var_set 'BOUNCER_USERNAME'
test_var_set 'BOUNCER_PASSWORD'

case $COT_PRODUCT in
  firefox)
    export TASKCLUSTER_SCOPE_PREFIX="project:releng:${PROJECT_NAME}:"
    ;;
  thunderbird)
    export TASKCLUSTER_SCOPE_PREFIX="project:comm:thunderbird:releng:${PROJECT_NAME}:"
    ;;
  *)
    exit 1
    ;;
esac
