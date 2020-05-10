#!/bin/bash
set -e errexit -o pipefail

test_var_set() {
  local varname=$1

  if [[ -z "${!varname}" ]]; then
    echo "error: ${varname} is not set"
    exit 1
  fi
}

#
# Check that all required variables exist
#
test_var_set 'CONFIG_DIR'
test_var_set 'CONFIG_LOADER'
test_var_set 'COT_PRODUCT'
test_var_set 'PROJECT_NAME'
test_var_set 'TEMPLATE_DIR'

export PASS_WORK_DIR=true

export PASSWORDS_PATH=$CONFIG_DIR/passwords.json

if [[ ! -f $PASSWORDS_PATH ]]; then
  echo "error: ${PASSWORDS_PATH} is missing"
fi
