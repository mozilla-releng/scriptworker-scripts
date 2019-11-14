#!/bin/bash
# This runs in docker to pin our requirements files.
SUFFIX=${SUFFIX:-txt}

pip install --upgrade pip
pip install pip-compile-multi

apt-get update
apt-get install -y libsodium-dev

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
    pushd $dir
    pip-compile-multi -g base -g test -o "$SUFFIX"
    chmod 644 requirements/*.txt
    popd
done
