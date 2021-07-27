#!/bin/bash
set +e

git clone https://github.com/mozilla/msix-packaging msix-packaging

cd msix-packaging
git checkout johnmcpms/signing

./makelinux.sh --pack

cd ..
