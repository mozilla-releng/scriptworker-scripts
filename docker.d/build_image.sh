#/bin/sh
set -e

test $DOCKER_REPO
test $DOCKER_TAG

# we include general docker.d scripts with docker image
cp ../docker.d/* docker.d/

docker build -f Dockerfile -t $DOCKER_REPO:$DOCKER_TAG .
docker save $DOCKER_REPO:$DOCKER_TAG > $1
