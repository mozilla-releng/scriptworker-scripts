#!/bin/bash

set -e

test $SIGNING_CERT


pwd

cd /home/worker/bin

source /home/worker/py3.5/bin/activate
scriptworker /home/worker/config.json



#python /home/worker/bin/funsize-balrog-submitter.py \
#    --artifacts-url-prefix "$PARENT_TASK_ARTIFACTS_URL_PREFIX" \
#    --manifest "$ARTIFACTS_DIR/manifest.json" \
#    -a "$BALROG_API_ROOT" \
#    --signing-cert "/home/worker/keys/${SIGNING_CERT}.pubkey" \
#    --verbose \
#    $EXTRA_BALROG_SUBMITTER_PARAMS
