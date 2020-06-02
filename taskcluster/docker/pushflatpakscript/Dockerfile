# %ARG DOCKER_IMAGE_PARENT
FROM $DOCKER_IMAGE_PARENT

VOLUME /builds/worker/checkouts
VOLUME /builds/worker/.cache

RUN apt-get update \
    && apt-get install -y gir1.2-ostree-1.0 libgirepository1.0-dev
