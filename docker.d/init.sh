#!/bin/bash
set -e

#
# Check for certain variables which should be set
#
test $PROJECT_NAME
test $ENV
test $COT_PRODUCT
test $TASKCLUSTER_CLIENT_ID
test $TASKCLUSTER_ACCESS_TOKEN
if [ "$ENV" == "prod" ]; then
  test $ED25519_PRIVKEY
fi

#
# Validate content of certain variables
#
case $ENV in
  prod)
    export TRUST_LEVEL=3
    export WORKER_SUFFIX=
    ;;
  fake-prod)
    export TRUST_LEVEL=1
    # special case for signing, using -t- instead
    if [ $PROJECT_NAME = "signing" ]; then
        export TRUST_LEVEL=t
    fi
    export WORKER_SUFFIX=
    ;;
  dev)
    export TRUST_LEVEL=1
    if [ $PROJECT_NAME = "signing" ]; then
        export TRUST_LEVEL=t
    fi
    export WORKER_SUFFIX="-dev"
    ;;
  *)
    exit 1
    ;;
esac
case $COT_PRODUCT in
  firefox)
    export TRUST_DOMAIN=gecko
    ;;
  thunderbird)
    export TRUST_DOMAIN=comm
    ;;
  mobile)
    export TRUST_DOMAIN=mobile
    ;;
  application-services)
    export TRUST_DOMAIN=appservices
    ;;
  *)
    exit 1
    ;;
esac

#
# Defaults
#
# For development purposes uncomment the following line when pushing to dev branch
# export $COT_PRODUCT="thunderbird|mobile|..."
export ARTIFACTS_DIR=/app/artifacts
export ARTIFACT_UPLOAD_TIMEOUT=1200
export CONFIG_DIR=/app/configs
export CONFIG_LOADER=/app/bin/configloader
export ED25519_PRIVKEY_PATH=$CONFIG_DIR/ed25519_privkey
export GITHUB_OAUTH_TOKEN=
export LOGS_DIR=/app/logs
export PROVISIONER_ID=scriptworker-k8s
export SCRIPTWORKER=/app/bin/scriptworker
export SIGN_CHAIN_OF_TRUST=false
if [ "$ENV" == "prod" ]; then
  export SIGN_CHAIN_OF_TRUST=true
fi
export TASK_CONFIG=$CONFIG_DIR/worker.json
export TASK_LOGS_DIR=$ARTIFACTS_DIR/public/logs
export TASK_MAX_TIMEOUT=3600
export TASK_SCRIPT=/app/bin/${PROJECT_NAME}script
export TEMPLATE_DIR=/app/docker.d
export VERBOSE=true
export VERIFY_CHAIN_OF_TRUST=true
export VERIFY_COT_SIGNATURE=false
if [ "$ENV" == "prod" ]; then
  export VERIFY_COT_SIGNATURE=true
fi
export WORK_DIR=/app/workdir
export WORKER_TYPE="${TRUST_DOMAIN}-${TRUST_LEVEL}-${PROJECT_NAME}${WORKER_SUFFIX}"
export WORKER_GROUP=${WORKER_TYPE}
export WORKER_ID_PREFIX="${WORKER_TYPE}-"

#
# ensure configuration folder exists we can write to it
#
mkdir -p -m 700 $CONFIG_DIR
echo $ED25519_PRIVKEY | base64 -d > $ED25519_PRIVKEY_PATH
chmod 600 $ED25519_PRIVKEY_PATH

#
# run worker specific configuration
#
source $(dirname $0)/init_worker.sh

#
# create scriptworker and workerscript configuration
#
$CONFIG_LOADER --worker-id-prefix=$WORKER_ID_PREFIX $TEMPLATE_DIR/scriptworker.yml $CONFIG_DIR/scriptworker.json
$CONFIG_LOADER $TEMPLATE_DIR/worker.yml $CONFIG_DIR/worker.json


# unset all of the variables to not potentially leak them
exec env - /app/bin/scriptworker /app/configs/scriptworker.json
