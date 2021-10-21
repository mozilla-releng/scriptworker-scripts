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
        githubscript
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

echo $DIRS | xargs -n4 -P4 docker run -t -v $PWD:/src -w /src python:3.9 maintenance/pin-helper.sh
echo $DIRS | xargs -n4 -P4 docker run -t -v $PWD:/src -e SUFFIX=py38.txt -w /src python:3.8 maintenance/pin-helper.sh
