#!/bin/bash
set +e

git clone --depth=1 https://github.com/mozilla/msix-packaging --branch johnmcpms/signing --single-branch msix-packaging

cd msix-packaging

./makelinux.sh --pack

cd ..
