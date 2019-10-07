#!/bin/bash
set -e

# == START: this is what we need to configure ==
test $AUTH0_CLIENT_ID
test $AUTH0_CLIENT_SECRET
# == END:   this is what we need to configure ==

case $ENV in
  dev|fake-prod)
    export API_ROOT="https://admin-stage.balrog.nonprod.cloudops.mozgcp.net/api"
    ;;
  prod)
    export API_ROOT="https://aus4-admin.mozilla.org/api"
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
        export AUTH0_AUDIENCE="balrog-stage"
        ;;
      prod)
        export AUTH0_AUDIENCE="balrog-prod"
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
