#!/bin/bash
set -e
test $IMAGE_TASK_ID
test $SECRET_URL
test $DOCKERHUB_EMAIL
test $DOCKERHUB_USER
test $TAG

dockerhub_password=$(curl $SECRET_URL | python -c 'import json, sys; a = json.load(sys.stdin); print a["secret"]["docker"]["password"]')

WORKDIR=$(mktemp -d)
cd $WORKDIR

curl -L -o image.tar https://queue.taskcluster.net/v1/task/$IMAGE_TASK_ID/artifacts/public/image.tar
docker load < image.tar
docker login -e $DOCKERHUB_EMAIL -u $DOCKERHUB_USER -p $dockerhub_password
docker push $TAG
