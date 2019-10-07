#!/bin/sh
set -e

test $DOCKERHUB_EMAIL
test $DOCKERHUB_USER
test $DOCKER_REPO
test $DOCKER_TAG
test $GIT_HEAD_REV
test $PUSH_DOCKER_IMAGE
test $SECRET_URL

apk -U add jq

echo "=== Re-tagging docker image ==="
export DOCKER_ARCHIVE_TAG="${DOCKER_TAG}-$(cat ./version.txt)-$(date +%Y%m%d%H%M%S)-${GIT_HEAD_REV}"
docker tag $DOCKER_REPO:$DOCKER_TAG $DOCKER_REPO:$DOCKER_ARCHIVE_TAG

echo "=== Logging to docker hub ==="
dockerhub_password=$(wget -qO- $SECRET_URL | jq '.["secret"]["docker"]["password"]')
docker login --email=$DOCKERHUB_EMAIL --username=$DOCKERHUB_USER --password=$dockerhub_password

echo "=== Pushing to docker hub ==="
docker push $DOCKER_REPO:$DOCKER_TAG
docker push $DOCKER_REPO:$DOCKER_ARCHIVE_TAG

echo "=== Clean up ==="
rm -f /root/.dockercfg
