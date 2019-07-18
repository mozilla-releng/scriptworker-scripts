#!/bin/sh
set -e
test $SECRET_URL
test $DOCKERHUB_EMAIL
test $DOCKERHUB_USER
test $DOCKER_REPO
test $DOCKER_TAG


echo "=== Logging to docker hub ==="
dockerhub_password=$(wget -qO- $SECRET_URL | jq '.["secret"]["docker"]["password"]')
docker login --email=$DOCKERHUB_EMAIL --username=$DOCKERHUB_USER --password=$dockerhub_password

echo "=== Pushing to docker hub ==="
docker push $DOCKER_REPO:$DOCKER_TAG
if [ "$DOCKER_RELEASE_TAG" = "" ]; then
  docker tag $DOCKER_REPO:$DOCKER_TAG $DOCKER_REPO:$DOCKER_RELEASE_TAG
  docker push $DOCKER_REPO:$DOCKER_RELEASE_TAG
fi
