#!/bin/bash
set -o errexit -o pipefail

test_var_set() {
  local varname=$1

  if [[ -z "${!varname}" ]]; then
    echo "error: ${varname} is not set"
    exit 1
  fi
}

case $COT_PRODUCT in
  mobile)
    case $ENV in
      prod|dev|fake-prod)
        test_var_set 'BITRISE_ACCESS_TOKEN'
        ;;
      *)
        exit 1
        ;;
    esac
    ;;
  *)
    exit 1
    ;;
esac
