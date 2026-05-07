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
    export API_ROOT="https://admin.stage.balrog.nonprod.webservices.mozgcp.net/api"
    export STAGE_API_ROOT="https://admin.stage.balrog.nonprod.webservices.mozgcp.net/api"
    ;;
  prod)
    export API_ROOT="https://aus4-admin.mozilla.org/api"
    export STAGE_API_ROOT="https://admin.stage.balrog.nonprod.webservices.mozgcp.net/api"
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
      # temporary environment to allow validation of new production environment
      # when `aus4-admin.mozilla.org` is pointed at mozcloud prod this can go away
      mozcloud-prod)
        export API_ROOT="https://admin.prod.balrog.prod.webservices.mozgcp.net/api"
        export AUTH0_AUDIENCE="balrog-production"
        ;;
      *)
        exit 1
        ;;
    esac
    export TASKCLUSTER_SCOPE_PREFIX="project:releng:${PROJECT_NAME}:"
    ;;
  xpi)
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
    export TASKCLUSTER_SCOPE_PREFIX="project:xpi:balrog:"
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
