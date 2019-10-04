#/bin/sh
set -e

test $DOCKER_REPO
test $DOCKER_TAG

echo $DOCKER_REPO
echo $DOCKER_TAG

echo "building docker image"
docker build -f Dockerfile -t $DOCKER_REPO:$DOCKER_TAG .

echo "saving docker image"
docker save $DOCKER_REPO:$DOCKER_TAG > $1
