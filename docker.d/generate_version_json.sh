#/bin/bash

set -xe
commit=$(git rev-parse HEAD)
version=$(cat version.txt)

cat > version.json <<EOF
{
    "commit": "${commit}",
    "version": "${version}",
    "source": "https://github.com/mozilla-releng/shipitscript",
    "build": "https://github.com/mozilla-releng/shipitscript/commit/${commit}"
}
EOF
