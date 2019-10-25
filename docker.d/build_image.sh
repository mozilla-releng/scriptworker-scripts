#/bin/sh
set -e

test $DOCKER_REPO
test $DOCKER_TAG

docker build -f Dockerfile -t $DOCKER_REPO:$DOCKER_TAG .
