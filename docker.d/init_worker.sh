#!/bin/bash
set -e

#
# Check that all required variables exist
#
test $COT_PRODUCT
test $PROJECT_NAME
test $BOUNCER_USERNAME
test $BOUNCER_PASSWORD
test $BOUNCER_USERNAME_NAZGUL
test $BOUNCER_PASSWORD_NAZGUL

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
