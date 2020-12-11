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
test_var_set 'CONFIG_DIR'
test_var_set 'COT_PRODUCT'
test_var_set 'PROJECT_NAME'
test_var_set 'SSH_KEY'

export UPSTREAM_REPO="https://hg.mozilla.org/mozilla-unified"
export MERGE_DAY_CLOBBER_FILE="CLOBBER"

case $COT_PRODUCT in
  firefox)
    test_var_set 'SSH_USER'
    export TASKCLUSTER_SCOPE_PREFIX="project:releng:${PROJECT_NAME}script:"
    ;;
  mobile)
    export TASKCLUSTER_SCOPE_PREFIX=""  # No prefix needed on mobile (and likely firefox, too)
    ;;
  thunderbird)
    test_var_set 'SSH_KEY'
    test_var_set 'SSH_USER'
    export TASKCLUSTER_SCOPE_PREFIX="project:comm:thunderbird:releng:${PROJECT_NAME}script:"
    export UPSTREAM_REPO=""
    export MERGE_DAY_CLOBBER_FILE=""
    ;;
  *)
    exit 1
    ;;
esac

export HG_SHARE_BASE_DIR=/tmp/share_base

export SSH_KEY_PATH=$CONFIG_DIR/ssh_key_$SSH_USER
echo $SSH_KEY | base64 -d > $SSH_KEY_PATH
chmod 400 $SSH_KEY_PATH

if [ -n "${SSH_MERGE_KEY}" ] && [ -n "${SSH_MERGE_USER}" ]; then
  export SSH_MERGE_KEY_PATH=$CONFIG_DIR/ssh_key_$SSH_MERGE_USER
  echo $SSH_MERGE_KEY | base64 -d > $SSH_MERGE_KEY_PATH
  chmod 400 $SSH_MERGE_KEY_PATH
else
  export SSH_MERGE_KEY_PATH=
  export SSH_MERGE_USER=
fi

mkdir /app/.ssh
chmod 700 /app/.ssh
cat > /app/.ssh/known_hosts << EOF
hg.mozilla.org,63.245.215.25 ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDEsS2fK+TVkHl4QvvOHB6R5xxngsSYJR+pA4+xDhw4mZT9tgCRU9BBG3LazSLp6PUxnpfok78475/tx6Z8QwbTyUTmLElZ9Z9eJzjaGz/olHzQSWv0VB3kT+VZt0LK7pEuaG+Ph/qwxbtUZZOApYLEvu8uctDlS66doofxZylbsgl1kpRQ5HNu+/DgVo9K9dyMOm9OLoy4tXHSE5pofn4tKYdFRa2lt6OVtIP5/hKNb2i0+JmgM8C3bJTPvzJ4C8p2h83ro29XPUkNAfWrgD5CmAPPqHFXyefDCfdefcvI8B8Za9v4j4LynBDZHsGfII+wIfzyLIxy9K6Op6nqDZgCciBRdgxh4uZQINEhB/JJP03Pxo42ExdG28oU3aL8kRRTORT5ehFtImFfr9QESHaUnbVzBbU5DmOB5voYDMle3RgyY+RXJ7+4OxjLRnJvGks9QCn8QrIvabs/PTCnenI8+yDhMlLUkWTiR4JK8vDBYB2Rm++EmVsN9WjllfDNg3Aj1aYe8XiBD4tS+lg7Ur4rJL8X20H4yMvq56sQ0qfH8PCIQGyGL725E7Yuwj/MHvou5xrPM/Lqo/MtX5T2njrzkeaBmI/zFJaLwbphdrwmrzepbcim7OYJFF2pz8u56KDPD1pUQ7C1gEIAx/4mHiDOGCYooSvyfD+JRdjkZUZMiQ==
hg.mozilla.org,63.245.215.102 ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDEsS2fK+TVkHl4QvvOHB6R5xxngsSYJR+pA4+xDhw4mZT9tgCRU9BBG3LazSLp6PUxnpfok78475/tx6Z8QwbTyUTmLElZ9Z9eJzjaGz/olHzQSWv0VB3kT+VZt0LK7pEuaG+Ph/qwxbtUZZOApYLEvu8uctDlS66doofxZylbsgl1kpRQ5HNu+/DgVo9K9dyMOm9OLoy4tXHSE5pofn4tKYdFRa2lt6OVtIP5/hKNb2i0+JmgM8C3bJTPvzJ4C8p2h83ro29XPUkNAfWrgD5CmAPPqHFXyefDCfdefcvI8B8Za9v4j4LynBDZHsGfII+wIfzyLIxy9K6Op6nqDZgCciBRdgxh4uZQINEhB/JJP03Pxo42ExdG28oU3aL8kRRTORT5ehFtImFfr9QESHaUnbVzBbU5DmOB5voYDMle3RgyY+RXJ7+4OxjLRnJvGks9QCn8QrIvabs/PTCnenI8+yDhMlLUkWTiR4JK8vDBYB2Rm++EmVsN9WjllfDNg3Aj1aYe8XiBD4tS+lg7Ur4rJL8X20H4yMvq56sQ0qfH8PCIQGyGL725E7Yuwj/MHvou5xrPM/Lqo/MtX5T2njrzkeaBmI/zFJaLwbphdrwmrzepbcim7OYJFF2pz8u56KDPD1pUQ7C1gEIAx/4mHiDOGCYooSvyfD+JRdjkZUZMiQ==
github.com ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6TbQa+PXYPCPy6rbTrTtw7PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsdlLJizHhbn2mUjvSAHQqZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+Se8xhHTvKSCZIFImWwoG6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOzQgqlJL3RKrTJvdsjE3JEAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA8VJiS5ap43JXiUFFAaQ==
EOF
