#!/bin/bash
set -o errexit -o pipefail

apt-get update
apt-get install --no-install-recommends -y gir1.2-ostree-1.0 libgirepository-2.0-0 ostree
apt-get clean
