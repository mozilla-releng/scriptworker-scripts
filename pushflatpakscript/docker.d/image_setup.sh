#!/bin/bash
set -o errexit -o pipefail

apt-get update
apt-get install --no-install-recommends -y ostree
apt-get clean
