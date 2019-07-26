#!/bin/bash
# We run this in scriptworker-scripts/. to pin all requirements.
set -e
set -x

docker run -t -v $PWD:/src -w /src python:3.7 "maintenance/pin-helper.sh"
docker run -t -v $PWD:/src -e SUFFIX=py36.txt -w /src python:3.6 "maintenance/pin-helper.sh"
