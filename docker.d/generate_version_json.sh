#/bin/sh
set -e

test $SCRIPTWORKER_HEAD_REV
test $TASK_ID
test $TASKCLUSTER_ROOT_URL
test $SCRIPTWORKER_HEAD_REPOSITORY

cat > version.json <<EOF
{
    "commit": "${SCRIPTWORKER_HEAD_REV}",
    "source": "${SCRIPTWORKER_HEAD_REPOSITORY}",
    "build": "${TASKCLUSTER_ROOT_URL}/tasks/${TASK_ID}"
}
EOF

cat version.json
