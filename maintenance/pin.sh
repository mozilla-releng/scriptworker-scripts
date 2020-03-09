#!/usr/bin/env bash
# We run this in scriptworker-scripts/. to pin all requirements.
set -e
set -x

if [ $# -gt 0 ]; then
    DIRS="$@"
else
    DIRS="
        addonscript
        balrogscript
        beetmoverscript
        bouncerscript
        configloader
        iscript
        notarization_poller
        pushapkscript
        pushflatpakscript
        pushsnapscript
        scriptworker_client
        shipitscript
        signingscript
        treescript
    "
fi

docker run -t -v $PWD:/src -w /src python:3.8 maintenance/pin-helper.sh $DIRS
docker run -t -v $PWD:/src -e SUFFIX=py37.txt -w /src python:3.7 maintenance/pin-helper.sh $DIRS
