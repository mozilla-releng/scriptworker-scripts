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
