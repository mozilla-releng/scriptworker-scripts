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

export MERGE_DAY_CLOBBER_FILE="CLOBBER"


case $COT_PRODUCT in
  firefox)
    test_var_set 'SSH_USER'
    test_var_set 'SSH_KEY'
    export REPO_TYPE="hg"
    export TRUST_DOMAIN="gecko"
    export UPSTREAM_REPO="https://hg.mozilla.org/mozilla-unified"
    ;;
  mobile)
    test_var_set 'GITHUB_PRIVKEY'
    export REPO_TYPE="git"
    export TRUST_DOMAIN="mobile"
    export UPSTREAM_REPO=""
    ;;
  thunderbird)
    test_var_set 'SSH_USER'
    test_var_set 'SSH_KEY'
    export REPO_TYPE="hg"
    export TRUST_DOMAIN="comm"
    export UPSTREAM_REPO="https://hg.mozilla.org/comm-unified"
    export MERGE_DAY_CLOBBER_FILE=""
    ;;
  *)
    exit 1
    ;;
esac

if [ "$REPO_TYPE" == "hg" ]; then
  export HG_SHARE_BASE_DIR=/tmp/share_base
  export SSH_KEY_PATH="$CONFIG_DIR/ssh_key_$SSH_USER"
  echo "$SSH_KEY" | base64 -d > "$SSH_KEY_PATH"
  chmod 400 "$SSH_KEY_PATH"

  if [ -n "${SSH_MERGE_KEY}" ] && [ -n "${SSH_MERGE_USER}" ]; then
    export SSH_MERGE_KEY_PATH="$CONFIG_DIR/ssh_key_$SSH_MERGE_USER"
    echo "$SSH_MERGE_KEY" | base64 -d > "$SSH_MERGE_KEY_PATH"
    chmod 400 "$SSH_MERGE_KEY_PATH"
  else
    export SSH_MERGE_KEY_PATH=
    export SSH_MERGE_USER=
  fi

  mkdir "$APP_DIR/.ssh"
  chmod 700 "$APP_DIR/.ssh"
  cat > "$APP_DIR/.ssh/known_hosts" << EOF
hg.mozilla.org,63.245.215.25 ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDEsS2fK+TVkHl4QvvOHB6R5xxngsSYJR+pA4+xDhw4mZT9tgCRU9BBG3LazSLp6PUxnpfok78475/tx6Z8QwbTyUTmLElZ9Z9eJzjaGz/olHzQSWv0VB3kT+VZt0LK7pEuaG+Ph/qwxbtUZZOApYLEvu8uctDlS66doofxZylbsgl1kpRQ5HNu+/DgVo9K9dyMOm9OLoy4tXHSE5pofn4tKYdFRa2lt6OVtIP5/hKNb2i0+JmgM8C3bJTPvzJ4C8p2h83ro29XPUkNAfWrgD5CmAPPqHFXyefDCfdefcvI8B8Za9v4j4LynBDZHsGfII+wIfzyLIxy9K6Op6nqDZgCciBRdgxh4uZQINEhB/JJP03Pxo42ExdG28oU3aL8kRRTORT5ehFtImFfr9QESHaUnbVzBbU5DmOB5voYDMle3RgyY+RXJ7+4OxjLRnJvGks9QCn8QrIvabs/PTCnenI8+yDhMlLUkWTiR4JK8vDBYB2Rm++EmVsN9WjllfDNg3Aj1aYe8XiBD4tS+lg7Ur4rJL8X20H4yMvq56sQ0qfH8PCIQGyGL725E7Yuwj/MHvou5xrPM/Lqo/MtX5T2njrzkeaBmI/zFJaLwbphdrwmrzepbcim7OYJFF2pz8u56KDPD1pUQ7C1gEIAx/4mHiDOGCYooSvyfD+JRdjkZUZMiQ==
hg.mozilla.org,63.245.215.102 ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDEsS2fK+TVkHl4QvvOHB6R5xxngsSYJR+pA4+xDhw4mZT9tgCRU9BBG3LazSLp6PUxnpfok78475/tx6Z8QwbTyUTmLElZ9Z9eJzjaGz/olHzQSWv0VB3kT+VZt0LK7pEuaG+Ph/qwxbtUZZOApYLEvu8uctDlS66doofxZylbsgl1kpRQ5HNu+/DgVo9K9dyMOm9OLoy4tXHSE5pofn4tKYdFRa2lt6OVtIP5/hKNb2i0+JmgM8C3bJTPvzJ4C8p2h83ro29XPUkNAfWrgD5CmAPPqHFXyefDCfdefcvI8B8Za9v4j4LynBDZHsGfII+wIfzyLIxy9K6Op6nqDZgCciBRdgxh4uZQINEhB/JJP03Pxo42ExdG28oU3aL8kRRTORT5ehFtImFfr9QESHaUnbVzBbU5DmOB5voYDMle3RgyY+RXJ7+4OxjLRnJvGks9QCn8QrIvabs/PTCnenI8+yDhMlLUkWTiR4JK8vDBYB2Rm++EmVsN9WjllfDNg3Aj1aYe8XiBD4tS+lg7Ur4rJL8X20H4yMvq56sQ0qfH8PCIQGyGL725E7Yuwj/MHvou5xrPM/Lqo/MtX5T2njrzkeaBmI/zFJaLwbphdrwmrzepbcim7OYJFF2pz8u56KDPD1pUQ7C1gEIAx/4mHiDOGCYooSvyfD+JRdjkZUZMiQ==
EOF
elif [ "$REPO_TYPE" == "git" ]; then
  export GITHUB_PRIVKEY_FILE="$CONFIG_DIR/github_privkey"
  echo "$GITHUB_PRIVKEY" | base64 -d > "$GITHUB_PRIVKEY_FILE"
  chmod 400 "$GITHUB_PRIVKEY_FILE"
fi
