#!/bin/bash
set -o errexit -o pipefail

test_var_set() {
  local varname=$1

  if [[ -z "${!varname}" ]]; then
    echo "error: ${varname} is not set"
    exit 1
  fi
}

# == START: this is what we need to configure ==
test_var_set 'JWT_USER'
test_var_set 'JWT_SECRET'
# == END:   this is what we need to configure ==

case $ENV in
  dev|fake-prod)
    export AMO_SERVER="https://addons.allizom.org"
    ;;
  prod)
    export AMO_SERVER="https://addons.mozilla.org"
    ;;
  *)
    exit 1
    ;;
esac

case $COT_PRODUCT in
  firefox)
    ;;
  *)
    exit 1
    ;;
esac

