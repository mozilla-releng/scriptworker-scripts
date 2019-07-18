#!/bin/sh
set -e
test $SECRET_URL
test $DOCKERHUB_EMAIL
test $DOCKERHUB_USER
test $DOCKER_TAG

dockerhub_password=$(curl $SECRET_URL | python -c 'import json, sys; a = json.load(sys.stdin); print a["secret"]["docker"]["password"]')

docker login -e $DOCKERHUB_EMAIL -u $DOCKERHUB_USER -p $dockerhub_password
docker push $DOCKER_REPO:$DOCKER_TAG
if [ "$DOCKER_RELEASE_TAG" = "" ]; then
  docker tag $DOCKER_REPO:$DOCKER_TAG $DOCKER_REPO:$DOCKER_RELEASE_TAG
  docker push $DOCKER_REPO:$DOCKER_RELEASE_TAG
fi
