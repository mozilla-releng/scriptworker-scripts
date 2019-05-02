#/bin/bash

set -xe
commit=$(git rev-parse HEAD)
version=$(cat beetmoverscript/_version.py | grep __version__ | awk -F'"' '{print $2}')

cat > version.json <<EOF
{
    "commit": "${commit}",
    "version": "${version}",
    "source": "https://github.com/mozilla-releng/beetmoverscript",
    "build": "https://tools.taskcluster.net/task-inspector/#${TASK_ID}"
}
EOF
