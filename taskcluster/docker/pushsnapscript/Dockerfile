# %ARG DOCKER_IMAGE_PARENT
FROM $DOCKER_IMAGE_PARENT

VOLUME /builds/worker/checkouts
VOLUME /builds/worker/.cache

RUN apt-get update \
    && apt-get install -y libsodium-dev
RUN truncate -s 0 /etc/os-release
