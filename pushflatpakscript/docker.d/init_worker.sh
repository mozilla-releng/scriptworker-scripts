#!/bin/bash
set -o errexit -o pipefail

test_var_set() {
  local varname=$1

  if [[ -z "${!varname}" ]]; then
    echo "error: ${varname} is not set"
    exit 1
  fi
}

case $ENV in
  dev|fake-prod)
    ;;
  prod)
    test_var_set 'REPO_TOKEN_BETA'
    test_var_set 'REPO_TOKEN_RELEASE'
    test_var_set 'REPO_TOKEN_ESR'
    export REPO_TOKEN_BETA_PATH=$CONFIG_DIR/beta_token.txt
    export REPO_TOKEN_RELEASE_PATH=$CONFIG_DIR/release_token.txt
    export REPO_TOKEN_ESR_PATH=$CONFIG_DIR/esr_token.txt
    echo $REPO_TOKEN_BETA | base64 -d > $REPO_TOKEN_BETA_PATH
    echo $REPO_TOKEN_RELEASE | base64 -d > $REPO_TOKEN_RELEASE_PATH
    echo $REPO_TOKEN_ESR | base64 -d > $REPO_TOKEN_ESR_PATH
    ;;
  *)
    exit 1
    ;;
esac

case $COT_PRODUCT in
  firefox)
    export FLATHUB_URL="https://hub.flathub.org"
  ;;
  *)
    exit 1
    ;;
esac
