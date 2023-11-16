#!/bin/bash
set -x -e -v

# This script is for building libdmg-hfsplus to get the `dmg` and `hfsplus`
# tools for handling DMG archives on Linux.

DEST=$1
if [ -d "$DEST" ]; then
  echo "Binaries will be installed to: $DEST"
else
  echo "Destination directory doesn't exist!"
  exit 1
fi

git clone --depth=1 --branch mozilla --single-branch https://github.com/mozilla/libdmg-hfsplus/ libdmg-hfsplus

pushd libdmg-hfsplus

# The openssl libraries in the sysroot cannot be linked in a PIE executable so we use -no-pie
cmake \
  -DOPENSSL_USE_STATIC_LIBS=1 \
  -DCMAKE_EXE_LINKER_FLAGS=-no-pie \
  .

make VERBOSE=1 -j$(nproc)

# We only need the dmg and hfsplus tools.
strip dmg/dmg hfs/hfsplus
cp dmg/dmg hfs/hfsplus "$DEST"

popd
rm -rf libdmg-hfsplus
echo "Done."
