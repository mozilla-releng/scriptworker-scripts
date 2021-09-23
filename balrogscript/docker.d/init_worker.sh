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
test_var_set 'AUTH0_CLIENT_ID'
test_var_set 'AUTH0_CLIENT_SECRET'
# == END:   this is what we need to configure ==

case $ENV in
  dev|fake-prod)
    export API_ROOT="https://admin-stage.balrog.nonprod.cloudops.mozgcp.net/api"
    export STAGE_API_ROOT="https://admin-stage.balrog.nonprod.cloudops.mozgcp.net/api"
    ;;
  prod)
    export API_ROOT="https://aus4-admin.mozilla.org/api"
    export STAGE_API_ROOT="https://admin-stage.balrog.nonprod.cloudops.mozgcp.net/api"
    ;;
  *)
    exit 1
    ;;
esac

case $COT_PRODUCT in
  firefox)
    case $ENV in
      dev|fake-prod)
        export AUTH0_AUDIENCE="balrog-cloudops-stage"
        ;;
      prod)
        export AUTH0_AUDIENCE="balrog-production"
        ;;
      *)
        exit 1
        ;;
    esac
    export TASKCLUSTER_SCOPE_PREFIX="project:releng:${PROJECT_NAME}:"
    ;;
  thunderbird)
    case $ENV in
      dev|fake-prod)
        export AUTH0_AUDIENCE="balrog-cloudops-stage"
        ;;
      prod)
        export AUTH0_AUDIENCE="balrog-production"
        ;;
      *)
        exit 1
        ;;
    esac
    export TASKCLUSTER_SCOPE_PREFIX="project:comm:thunderbird:releng:${PROJECT_NAME}:"
    ;;
  *)
    exit 1
    ;;
esac

export AUTH0_DOMAIN="auth.mozilla.auth0.com"
