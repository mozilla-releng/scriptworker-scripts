# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

FROM ghcr.io/astral-sh/uv:0.7.15-bookworm
ARG  PYTHON_VERSION

ENV UV_PYTHON_INSTALL_DIR=/python
ENV UV_PYTHON_PREFERENCE=only-managed
ENV UV_LINK_MODE=copy
ENV UV_PYTHON=${PYTHON_VERSION}
RUN uv python install ${UV_PYTHON}

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
