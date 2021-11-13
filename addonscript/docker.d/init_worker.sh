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



case $COT_PRODUCT in
  firefox)
    export TASKCLUSTER_SCOPE_PREFIX="project:releng:addons.mozilla.org:server"
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
    ;;
  thunderbird)
      export TASKCLUSTER_SCOPE_PREFIX="project:comm:thunderbird:releng:addons.thunderbird.net:server"
      case $ENV in
        dev|fake-prod)
          export AMO_SERVER="https://addons-stage.thunderbird.net"
          ;;
        prod)
          export AMO_SERVER="https://addons.thunderbird.net"
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

