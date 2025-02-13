#!/usr/bin/env bash
set -e
# Set pipefail so curl failures are caught before the pipe to jq
set -o pipefail  # This will fail on sh / only works on bash

test $APP
test $DOCKER_TAG
test $DOCKER_ARCHIVE_TAG
test $DOCKER_REPO
test $MOZ_FETCHES_DIR
test $TASKCLUSTER_ROOT_URL
test $TASK_ID
test $VCS_HEAD_REPOSITORY
test $VCS_HEAD_REV

echo "=== Generating dockercfg ==="
PASSWORD_URL=http://taskcluster/secrets/v1/secret/project/releng/scriptworker-scripts/deploy
mkdir -m 700 $HOME/.docker
# curl --fail forces curl to return a non-zero exit code if the response isn't HTTP 200 (i.e.: HTTP 403 Unauthorized)
curl --fail -v $PASSWORD_URL | jq '.secret.dockercfg' > $HOME/.docker/config.json
chmod 600 $HOME/.docker/config.json

cd $MOZ_FETCHES_DIR
unzstd image.tar.zst

echo "=== Inserting version.json into image ==="
# Create an OCI copy of image in order umoci can patch it
skopeo copy docker-archive:image.tar oci:${APP}:final

cat > version.json <<EOF
{
    "commit": "${VCS_HEAD_REV}",
    "source": "${VCS_HEAD_REPOSITORY}",
    "build": "${TASKCLUSTER_ROOT_URL}/tasks/${TASK_ID}"
}
EOF

umoci insert --image ${APP}:final version.json /app/version.json

echo "=== Pushing to docker hub ==="
skopeo copy oci:${APP}:final docker://$DOCKER_REPO:$DOCKER_TAG
skopeo copy oci:${APP}:final docker://$DOCKER_REPO:$DOCKER_ARCHIVE_TAG
skopeo inspect docker://$DOCKER_REPO:$DOCKER_TAG

echo "=== Clean up ==="
rm -rf $HOME/.docker
