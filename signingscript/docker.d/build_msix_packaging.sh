#!/bin/bash
set +e

git clone https://github.com/mozilla/msix-packaging msix-packaging

cd msix-packaging
git checkout signing2

./makelinux.sh --pack

cd ..
