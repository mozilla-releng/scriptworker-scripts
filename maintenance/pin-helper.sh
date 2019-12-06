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

<<<<<<< HEAD
for dir in \
    addonscript \
    balrogscript \
    beetmoverscript \
    bouncerscript \
    configloader \
    iscript \
    pushapkscript \
    pushsnapscript \
    scriptworker_client \
    shipitscript \
    signingscript \
    treescript \
    ; do
=======
for dir in $DIRS; do
>>>>>>> ab343fa550d3d19d968795e4c5a91caf52ea3108
    pushd $dir
    pip-compile-multi -g base -g test -o "$SUFFIX"
    chmod 644 requirements/*.txt
    popd
done
