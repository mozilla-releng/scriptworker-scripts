#!/bin/sh
set -e

test $DOCKERHUB_EMAIL
test $DOCKERHUB_USER
test $DOCKER_REPO
test $DOCKER_TAG
test $SCRIPTWORKER_HEAD_REV
test $HOME
test $PUSH_DOCKER_IMAGE
test $SECRET_URL
test $PROJECT_NAME

apk -U add jq

echo "=== Re-tagging docker image ==="
export DOCKER_ARCHIVE_TAG="${DOCKER_TAG}-$(date +%Y%m%d%H%M%S)-${SCRIPTWORKER_HEAD_REV}"
docker tag $DOCKER_REPO:$DOCKER_TAG $DOCKER_REPO:$DOCKER_ARCHIVE_TAG

echo "=== Generating dockercfg ==="
# docker login stopped working in Taskcluster for some reason
wget -qO- $SECRET_URL | jq '.secret.docker.dockercfg' > $HOME/.dockercfg
chmod 600 $HOME/.dockercfg

echo "=== Pushing to docker hub ==="
docker push $DOCKER_REPO:$DOCKER_TAG
docker push $DOCKER_REPO:$DOCKER_ARCHIVE_TAG

echo "=== Clean up ==="
rm -f $HOME/.dockercfg
