#!/bin/bash
set -o errexit -o pipefail

apt-get update
apt-get install -y gir1.2-ostree-1.0 libgirepository1.0-dev
apt-get clean
