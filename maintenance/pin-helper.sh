#!/bin/bash
# This runs in docker to pin our requirements files.
set -e
SUFFIX=${SUFFIX:-txt}

# Supress pip root user warning
export PIP_ROOT_USER_ACTION=ignore

if [ $# -gt 0 ]; then
    DIRS="$@"
else
    echo "Usage: pin-helper.sh [script(s)]"
    exit 1
fi

for dir in $DIRS; do
    ARGS="$EXTRA_ARGS -g base -g test -g local"
    if [ "$dir" = "pushflatpakscript" ]; then
        ARGS="$ARGS -g flat-manager"
    fi
    echo $ARGS
    if [ "$dir" = "." ]; then
        ARGS="$EXTRA_ARGS -g test"
    fi
    pushd "$dir"
    pip-compile-multi -o "$SUFFIX" $ARGS
    chmod 644 requirements/*.txt
    popd
done
