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
apt-get install -y \
    gir1.2-ostree-1.0 \
    libgirepository1.0-dev \
    libsodium-dev

for dir in $DIRS; do
    ARGS="-g base -g test -g local"
    if [ $dir = "pushflatpakscript" ]; then
        ARGS="$ARGS -g flat-manager"
    fi
    pushd $dir
    pip-compile-multi -o "$SUFFIX" $ARGS
    chmod 644 requirements/*.txt
    popd
done
