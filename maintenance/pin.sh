#!/usr/bin/env bash
# We run this in scriptworker-scripts/. to pin all requirements.
set -e
set -x

EXTRA_ARGS=${EXTRA_ARGS:-""}

if [ $# -gt 0 ]; then
    DIRS="$@"
else
    DIRS="
        addonscript
        balrogscript
        beetmoverscript
        bouncerscript
        configloader
        githubscript
        iscript
        notarization_poller
        pushapkscript
        pushflatpakscript
        pushmsixscript
        scriptworker_client
        shipitscript
        signingscript
        treescript
    "
fi

RUNCMD="RUN apt-get update && \
    apt-get install -y \
        gir1.2-ostree-1.0 \
        libgirepository1.0-dev \
        libsodium-dev && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --upgrade pip && \
    pip install pip-compile-multi
"

echo -e "FROM python:3.8\n${RUNCMD}" | docker build --pull --tag "scriptworker-script-pin:3.8" -
echo -e "FROM python:3.9\n${RUNCMD}" | docker build --pull --tag "scriptworker-script-pin:3.9" -


echo $DIRS | xargs -n8 -P8 time docker run --rm -t -v "$PWD":/src -e EXTRA_ARGS="$EXTRA_ARGS" -w /src scriptworker-script-pin:3.9 maintenance/pin-helper.sh
echo $DIRS | xargs -n8 -P8 time docker run --rm -t -v "$PWD":/src -e EXTRA_ARGS="$EXTRA_ARGS" -e SUFFIX=py38.txt -w /src scriptworker-script-pin:3.8 maintenance/pin-helper.sh
