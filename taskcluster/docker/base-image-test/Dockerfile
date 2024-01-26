# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

ARG DOCKER_IMAGE_PARENT
FROM $DOCKER_IMAGE_PARENT

VOLUME /builds/worker/checkouts
VOLUME /builds/worker/.cache

RUN ln -s /app/docker.d/healthcheck /bin/healthcheck

ARG APT_PACKAGES
# Add worker user and install requirements
RUN apt-get update \
 && apt-get install -y ${APT_PACKAGES} \
 && apt-get clean \
 && groupadd --gid 1000 worker \
 && useradd -g worker --uid 1000 --shell /bin/bash --create-home --home-dir /worker -o worker \
 && mkdir -p /builds/worker/artifacts \
 && chown worker:worker -R /builds/worker \
 && pip install -U pip tox

# %include-run-task
ENV SHELL=/bin/bash \
    HOME=/builds/worker \
    PATH=/builds/worker/.local/bin:$PATH

# Set a default command useful for debugging
CMD ["/bin/bash", "--login"]
