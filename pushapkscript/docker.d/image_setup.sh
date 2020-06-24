#!/bin/bash
set -o errexit -o pipefail

apt-get update
apt-get install -y default-jdk
apt-get clean
