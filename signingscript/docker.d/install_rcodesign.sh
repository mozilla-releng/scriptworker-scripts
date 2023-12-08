#!/bin/bash
set -x -e -v

DEST=$1
if [ -d "$DEST" ]; then
  echo "Binaries will be installed to: $DEST"
else
  echo "Destination directory doesn't exist!"
  exit 1
fi


wget -qO- https://github.com/indygreg/apple-platform-rs/releases/download/apple-codesign%2F0.26.0/apple-codesign-0.26.0-x86_64-unknown-linux-musl.tar.gz \
 | tar xvz -C "$DEST" --transform 's/.*\///g' --wildcards --no-anchored 'rcodesign'

chmod +x "${DEST}/rcodesign"
