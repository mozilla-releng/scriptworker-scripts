ARG DOCKER_IMAGE_PARENT
FROM $DOCKER_IMAGE_PARENT

VOLUME /builds/worker/checkouts
VOLUME /builds/worker/.cache

# %include pushapkscript/docker.d/image_setup.sh
COPY topsrcdir/pushapkscript/docker.d/image_setup.sh /usr/local/bin/

RUN image_setup.sh
