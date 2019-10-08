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
    test_var_set 'MACAROON_BETA'
    test_var_set 'MACAROON_CANDIDATE'
    test_var_set 'MACAROON_ESR'
    export MACAROON_BETA_PATH=$CONFIG_DIR/beta_macaroon.cfg
    export MACAROON_CANDIDATE_PATH=$CONFIG_DIR/candidate_macaroon.cfg
    export MACAROON_ESR_PATH=$CONFIG_DIR/esr_macaroon.cfg
    echo $MACAROON_BETA | base64 -d > $MACAROON_BETA_PATH
    echo $MACAROON_CANDIDATE | base64 -d > $MACAROON_CANDIDATE_PATH
    echo $MACAROON_ESR | base64 -d > $MACAROON_ESR_PATH
    ;;
  *)
    exit 1
    ;;
esac

case $COT_PRODUCT in
  firefox) ;;
  *)
    exit 1
    ;;
esac
