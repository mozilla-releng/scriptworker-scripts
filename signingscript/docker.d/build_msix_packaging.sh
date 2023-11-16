#!/bin/bash
set +e

git clone --depth=1 https://github.com/mozilla/msix-packaging --branch johnmcpms/signing --single-branch msix-packaging

cd msix-packaging

./makelinux.sh --pack

cd ..

cp msix-packaging/.vs/bin/makemsix /usr/bin
cp msix-packaging/.vs/lib/libmsix.so /usr/lib

rm -rf msix-packaging
