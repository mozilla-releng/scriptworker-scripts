ARG DOCKER_IMAGE_PARENT
FROM $DOCKER_IMAGE_PARENT

VOLUME /builds/worker/checkouts
VOLUME /builds/worker/.cache

RUN apt-get update && \
    apt-get -y install osslsigncode && \
    apt-get clean
