#!/bin/bash
set -o errexit -o pipefail

PKGS="${@:-libsodium-dev}"

apt-get update
for pkg in $PKGS; do
    apt-get install -y $pkg
done
apt-get clean
# XXX Avoid snapcraft from loading useless libs when running on Ubuntu
truncate -s 0 /etc/os-release
