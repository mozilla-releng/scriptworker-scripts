ARG DOCKER_IMAGE_PARENT
FROM $DOCKER_IMAGE_PARENT

VOLUME /builds/worker/checkouts
VOLUME /builds/worker/.cache

# %include pushmsixscript/docker.d/image_setup.sh
COPY topsrcdir/pushmsixscript/docker.d/image_setup.sh /usr/local/bin/

RUN image_setup.sh
