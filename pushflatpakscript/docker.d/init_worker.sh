#!/bin/bash
set -o errexit -o pipefail

test_var_set() {
  local varname=$1

  if [[ -z "${!varname}" ]]; then
    echo "error: ${varname} is not set"
    exit 1
  fi
}

test_var_set 'FLATHUB_URL'
test_var_set 'TASKCLUSTER_ROOT_URL'

export FLAT_MANAGER_CLIENT=/app/flat_manager_venv/bin/flat-manager-client

case $ENV in
  dev|fake-prod)
    ;;
  prod)
    test_var_set 'REPO_TOKEN_BETA'
    test_var_set 'REPO_TOKEN_STABLE'
    export REPO_TOKEN_BETA_PATH=$CONFIG_DIR/beta_token.txt
    export REPO_TOKEN_STABLE_PATH=$CONFIG_DIR/stable_token.txt
    echo $REPO_TOKEN_BETA | base64 -d > $REPO_TOKEN_BETA_PATH
    echo $REPO_TOKEN_STABLE | base64 -d > $REPO_TOKEN_STABLE_PATH
    ;;
  *)
    exit 1
    ;;
esac

case $COT_PRODUCT in
  firefox)
    export APP_ID="org.mozilla.firefox"
    export TASKCLUSTER_SCOPE_PREFIX="project:releng:flathub:firefox:"
    ;;
  thunderbird)
    export APP_ID="org.mozilla.Thunderbird"
    export TASKCLUSTER_SCOPE_PREFIX="project:comm:thunderbird:releng:flathub:"
    ;;
  *)
    exit 1
    ;;
esac
