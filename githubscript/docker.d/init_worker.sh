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
  mobile|xpi)
    case $ENV in
      dev|fake-prod)
        test_var_set 'GITHUB_TOKEN_WRITE_ACCESS_STAGING'
        ;;
      prod)
        test_var_set 'GITHUB_TOKEN_WRITE_ACCESS_PROD'
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
