#!/bin/bash
set -o errexit -o pipefail

test_var_set() {
  local varname=$1

  if [[ -z "${!varname}" ]]; then
    echo "error: ${varname} is not set"
    exit 1
  fi
}

export REQUEST_TIMEOUT_SECONDS=90
export LOGIN_URL=https://login.microsoftonline.com
export TOKEN_RESOURCE=https://manage.devcenter.microsoft.com
export STORE_URL=https://manage.devcenter.microsoft.com/v1.0/my/applications/
export MOCK_APPLICATION_ID=MOCK-APP-ID
export RELEASE_ROLLOUT_PERCENTAGE=25.0

case $COT_PRODUCT in
  firefox)
    export BETA_APPLICATION_ID=9NZW26FRNDLN
    export RELEASE_APPLICATION_ID=9NZVDKPMR9RD
    export TASKCLUSTER_SCOPE_PREFIX=project:releng:microsoftstore:
    ;;
  thunderbird)
    export BETA_APPLICATION_ID=9PFQWVMSS45P
    export RELEASE_APPLICATION_ID=9PM5VM1S3VMQ
    export TASKCLUSTER_SCOPE_PREFIX=project:comm:thunderbird:releng:microsoftstore:
    ;;
  *)
    echo "FAIL: Unsupported product: ${COT_PRODUCT}" >&2
    exit 1
    ;;
esac


case $ENV in
  dev|fake-prod)
      case $COT_PRODUCT in
        # dev and fake-prod do not have variables set
        firefox|thunderbird)
          ;;
        *)
          echo "FAIL: Unsupported product in dev environment: ${COT_PRODUCT}" >&2
          exit 1
          ;;
      esac
      ;;
  prod)
    case $COT_PRODUCT in
      firefox|thunderbird)
        # For firefox prod environment
        test_var_set 'TENANT_ID'
        test_var_set 'CLIENT_ID'
        test_var_set 'CLIENT_SECRET'
        export TENANT_ID=$(echo "$TENANT_ID" | base64 -d)
        export CLIENT_ID=$(echo "$CLIENT_ID" | base64 -d)
        export CLIENT_SECRET=$(echo "$CLIENT_SECRET" | base64 -d)
        ;;
      *)
        # Unsupported product in prod environment
        echo "FAIL: Unsupported product in prod environment: ${COT_PRODUCT}" >&2
        exit 1
        ;;
    esac
    ;;
  *)
    # Unsupported environment
    echo "FAIL: Unsupported environment: ${ENV}" >&2
    exit 1
    ;;
esac
