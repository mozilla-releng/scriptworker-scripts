#!/bin/bash
set -e
test $SECRET_URL
test $DOCKERHUB_EMAIL
test $DOCKERHUB_USER
test $TAG

dockerhub_password=$(curl $SECRET_URL | python -c 'import json, sys; a = json.load(sys.stdin); print a["secret"]["docker"]["password"]')

docker login -e $DOCKERHUB_EMAIL -u $DOCKERHUB_USER -p $dockerhub_password
docker push $TAG
