#!/bin/bash
set -o errexit -o pipefail

PKGS="${@:-libsodium-dev}"

apt-get update
for pkg in $PKGS; do
    apt-get install -y $pkg
done
apt-get clean
