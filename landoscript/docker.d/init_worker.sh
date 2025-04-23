#!/bin/bash
set -o errexit -o pipefail

test_var_set() {
  local varname=$1

  if [[ -z "${!varname}" ]]; then
    echo "error: ${varname} is not set"
    exit 1
  fi
}

test_var_set "CONFIG_DIR"
test_var_set "LANDO_TOKEN"
test_var_set "GITHUB_PRIVATE_KEY"

if [ "$ENV" == "prod" ]; then
  export LANDO_API="https://lando.moz.tools/api"
else
  export LANDO_API="https://dev.lando.nonprod.webservices.mozgcp.net/api"
fi

export GITHUB_PRIVATE_KEY_FILE="${CONFIG_DIR}/github_private_key"
echo "${GITHUB_PRIVATE_KEY}" + base64 -d > "${GITHUB_PRIVATE_KEY_FILE}"
chmod 400 "${GITHUB_PRIVATE_KEY_FILE}"
