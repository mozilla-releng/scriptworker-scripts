#!/bin/bash

docker build --pull -t balrogworkertest .
docker run --rm --entrypoint /app/bin/test_entrypoint.sh balrogworkertest

