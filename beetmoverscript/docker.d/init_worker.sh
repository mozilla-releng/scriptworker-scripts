#!/bin/bash
set -o errexit -o pipefail

test_var_set() {
  local varname=$1

  if [[ -z "${!varname}" ]]; then
    echo "error: ${varname} is not set"
    exit 1
  fi
}

case $COT_PRODUCT in
  firefox)
    case $ENV in
      dev|fake-prod)
        test_var_set 'DEP_ID'
        test_var_set 'DEP_KEY'
        test_var_set 'DEP_PARTNER_ID'
        test_var_set 'DEP_PARTNER_KEY'
        test_var_set 'MAVEN_ID'
        test_var_set 'MAVEN_KEY'
        ;;
      prod)
        test_var_set 'NIGHTLY_ID'
        test_var_set 'NIGHTLY_KEY'
        test_var_set 'RELEASE_ID'
        test_var_set 'RELEASE_KEY'
        test_var_set 'PARTNER_ID'
        test_var_set 'PARTNER_KEY'
        test_var_set 'DEP_ID'
        test_var_set 'DEP_KEY'
        test_var_set 'DEP_PARTNER_ID'
        test_var_set 'DEP_PARTNER_KEY'
        test_var_set 'MAVEN_ID'
        test_var_set 'MAVEN_KEY'
        ;;
      *)
        exit 1
        ;;
    esac
    ;;
  thunderbird)
    case $ENV in
      dev|fake-prod)
        test_var_set 'DEP_ID'
        test_var_set 'DEP_KEY'
        ;;
      prod)
        test_var_set 'NIGHTLY_ID'
        test_var_set 'NIGHTLY_KEY'
        test_var_set 'RELEASE_ID'
        test_var_set 'RELEASE_KEY'
        test_var_set 'DEP_ID'
        test_var_set 'DEP_KEY'
        ;;
      *)
        exit 1
        ;;
    esac
    ;;
  mobile)
    case $ENV in
      dev|fake-prod)
        test_var_set 'MAVEN_ID'
        test_var_set 'MAVEN_KEY'
        test_var_set 'MAVEN_NIGHTLY_ID'
        test_var_set 'MAVEN_NIGHTLY_KEY'
        test_var_set 'DEP_ID'
        test_var_set 'DEP_KEY'
        ;;
      prod)
        test_var_set 'MAVEN_ID'
        test_var_set 'MAVEN_KEY'
        test_var_set 'MAVEN_NIGHTLY_ID'
        test_var_set 'MAVEN_NIGHTLY_KEY'
        test_var_set 'DEP_ID'
        test_var_set 'DEP_KEY'
        test_var_set 'NIGHTLY_ID'
        test_var_set 'NIGHTLY_KEY'
        test_var_set 'RELEASE_ID'
        test_var_set 'RELEASE_KEY'
        ;;
      *)
        exit 1
        ;;
    esac
    ;;
  app-services)
    test_var_set 'MAVEN_ID'
    test_var_set 'MAVEN_KEY'
    ;;
  glean)
    test_var_set 'MAVEN_ID'
    test_var_set 'MAVEN_KEY'
    ;;
  *)
    exit 1
    ;;
esac
