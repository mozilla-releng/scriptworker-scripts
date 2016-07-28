#!/bin/bash

#python2 tools/archiver_client.py buildtools --repo build/tools --rev f6455ec0b09d --subdir lib/python --destination tools

docker build --pull -t balrogworkertest .
docker run --rm --entrypoint /app/test_entrypoint.sh balrogworkertest

