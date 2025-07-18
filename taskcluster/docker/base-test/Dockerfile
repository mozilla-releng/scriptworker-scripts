# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

ARG PYTHON_VERSION
ARG UV_VERSION

FROM ghcr.io/astral-sh/uv:$UV_VERSION AS uv
FROM python:$PYTHON_VERSION

COPY --from=uv /uv /bin

ENV UV_LINK_MODE=copy

# Add worker user
RUN mkdir /builds && \
    groupadd -g 1000 -o worker && \
    useradd -d /builds/worker -s /bin/bash -m worker -g 1000 -o -u 1000 && \
    mkdir /builds/worker/artifacts && \
    chown worker:worker /builds/worker/artifacts

RUN ln -s /app/docker.d/healthcheck /bin/healthcheck

ARG APT_PACKAGES
# Install extra requirements
RUN /bin/sh -c "if [ \"${APT_PACKAGES}\" != \"\" ]; then apt-get update && apt-get install -y ${APT_PACKAGES} && apt-get clean; fi"

# %include-run-task
ENV SHELL=/bin/bash \
    HOME=/builds/worker \
    PATH=/builds/worker/.local/bin:$PATH

VOLUME /builds/worker/checkouts
VOLUME /builds/worker/.cache


# Set a default command useful for debugging
CMD ["/bin/bash", "--login"]
