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


    if [ "$COT_PRODUCT" = thunderbird ]; then
      # test_var_set 'REPO_TOKEN_RELEASE'
      # must either have REPO_TOKEN_RELEASE or REPO_TOKEN_ESR defined
      if [[ -z "$REPO_TOKEN_RELEASE" ]] && [[ -z "$REPO_TOKEN_ESR" ]]; then
        echo "error: must have token defined for release or esr channel"
        exit 1
      fi

      export REPO_TOKEN_RELEASE_PATH=$CONFIG_DIR/release_token.txt
      echo $REPO_TOKEN_RELEASE | base64 -d > $REPO_TOKEN_RELEASE_PATH

      export REPO_TOKEN_ESR_PATH=$CONFIG_DIR/esr_token.txt
      echo $REPO_TOKEN_ESR | base64 -d > $REPO_TOKEN_ESR_PATH
    fi
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
    export APP_ID_RELEASE="org.mozilla.ThunderbirdRelease"
    export APP_ID_ESR="org.mozilla.ThunderbirdESR"
    export TASKCLUSTER_SCOPE_PREFIX="project:comm:thunderbird:releng:flathub:"
    ;;
  *)
    exit 1
    ;;
esac
