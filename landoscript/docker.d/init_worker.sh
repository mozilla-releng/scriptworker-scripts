#!/bin/bash
set -o errexit -o pipefail

test_var_set() {
  local varname=$1

  if [[ -z "${!varname}" ]]; then
    echo "error: ${varname} is not set"
    exit 1
  fi
}

# TODO: real URLs
if [ "$ENV" == "prod" ]; then
  export LANDO_API="https://lando.prod"
else
  export LANDO_API="https://lando.dev"
fi

test_var_set "LANDO_TOKEN"
