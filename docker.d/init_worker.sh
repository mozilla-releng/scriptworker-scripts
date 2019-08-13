#!/bin/bash
set -e

case $COT_PRODUCT in
  firefox)
    case $ENV in
      dev|fake-prod)
        test DEP_ID
        test DEP_KEY
        test DEP_PARTNER_ID
        test DEP_PARTNER_KEY
        test MAVEN_ID
        test MAVEN_KEY
        ;;
      prod)
        test NIGHTLY_ID
        test NIGHTLY_KEY
        test RELEASE_ID
        test RELEASE_KEY
        test PARTNER_ID
        test PARTNER_KEY
        test DEP_ID
        test DEP_KEY
        test DEP_PARTNER_ID
        test DEP_PARTNER_KEY
        test MAVEN_ID
        test MAVEN_KEY
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
        test DEP_ID
        test DEP_KEY
        ;;
      prod)
        test NIGHTLY_ID
        test NIGHTLY_KEY
        test RELEASE_ID
        test RELEASE_KEY
        test DEP_ID
        test DEP_KEY
        ;;
      *)
        exit 1
        ;;
    esac
    export TASKCLUSTER_SCOPE_PREFIX="project:comm:thunderbird:releng:${PROJECT_NAME}:"
    ;;
  mobile)
    test MAVEN_ID
    test MAVEN_KEY
    test MAVEN_SNAPSHOT_ID
    test MAVEN_SNAPSHOT_KEY
    export TASKCLUSTER_SCOPE_PREFIX="project:mobile:android-components:releng:${PROJECT_NAME}:"
    ;;
  application-services)
    test MAVEN_ID
    test MAVEN_KEY
    export TASKCLUSTER_SCOPE_PREFIX="project:mozilla:application-services:releng:${PROJECT_NAME}:"
    ;;
  *)
    exit 1
    ;;
esac
