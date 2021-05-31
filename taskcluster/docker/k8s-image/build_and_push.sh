#!/bin/sh
# TODO: move docker.d/ files into the image?
set -e
test SCRIPTWORKER_HEAD_REPOSITORY
test SCRIPTWORKER_HEAD_REV
test PROJECT_NAME
test PUSH_DOCKER_IMAGE

mkdir -p /builds/worker/checkouts
cd /builds/worker/checkouts
wget ${SCRIPTWORKER_HEAD_REPOSITORY}/archive/${SCRIPTWORKER_HEAD_REV}.tar.gz
tar zxf ${SCRIPTWORKER_HEAD_REV}.tar.gz
mv *-${SCRIPTWORKER_HEAD_REV} src
cd src
cp -arv ${PROJECT_NAME}/docker.d/* docker.d/
cp ${PROJECT_NAME}/Dockerfile .
sh ./docker.d/generate_version_json.sh
sh ./docker.d/build_image.sh
if [ "${PUSH_DOCKER_IMAGE}" == "1" ]; then
  ./docker.d/push_image.sh
fi
