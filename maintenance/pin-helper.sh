#!/bin/bash
# This runs in docker to pin our requirements files.
set -e
SUFFIX=${SUFFIX:-txt}
if [ $# -gt 0 ]; then
    DIRS="$@"
else
    echo "Usage: pin-helper.sh [script(s)]"
    exit 1
fi

pip install --upgrade pip
pip install pip-compile-multi

apt-get update
apt-get install -y libsodium-dev

for dir in $DIRS; do
    pushd $dir
    pip-compile-multi -g base -g test -o "$SUFFIX"
    chmod 644 requirements/*.txt
    popd
done
