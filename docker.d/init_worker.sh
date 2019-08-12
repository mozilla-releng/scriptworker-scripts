#!/bin/bash
set -e

# 
# Check that all required variables exist
#
test $CONFIG_DIR
test $COT_PRODUCT
test $PROJECT_NAME
test $SSH_KEY
test $SSH_USER

case $COT_PRODUCT in
  firefox)
    export TASKCLUSTER_SCOPE_PREFIX="project:releng:${PROJECT_NAME}script:"
    ;;
  thunderbird)
    export TASKCLUSTER_SCOPE_PREFIX="project:comm:thunderbird:releng:${PROJECT_NAME}script:"
    ;;
  *)
    exit 1
    ;;
esac

export HG_SHARE_BASE_DIR=/tmp/share_base
export SSH_KEY_PATH=$CONFIG_DIR/ssh_key_$SSH_USER

echo $SSH_KEY | base64 -d > $SSH_KEY_PATH
