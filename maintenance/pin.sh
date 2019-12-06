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
        pushapkscript
        pushsnapscript
        scriptworker_client
        shipitscript
        signingscript
        treescript
    "
fi

for dir in $DIRS; do
    docker run -t -v $PWD:/src -w /src python:3.7 maintenance/pin-helper.sh "$dir"
    docker run -t -v $PWD:/src -e SUFFIX=py38.txt -w /src python:3.8 maintenance/pin-helper.sh "$dir"
done
