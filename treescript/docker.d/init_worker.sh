#!/bin/bash
set -o errexit -o pipefail

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
test_var_set 'APP_DIR'
test_var_set 'CONFIG_DIR'
test_var_set 'COT_PRODUCT'
test_var_set 'PROJECT_NAME'
test_var_set 'GITHUB_PRIVKEY'

case $COT_PRODUCT in
  mobile)
    export TRUST_DOMAIN="mobile"
    ;;
  *)
    exit 1
    ;;
esac

export GITHUB_PRIVKEY_FILE="$CONFIG_DIR/github_privkey"
echo "$GITHUB_PRIVKEY" | base64 -d > "$GITHUB_PRIVKEY_FILE"
chmod 400 "$GITHUB_PRIVKEY_FILE"
