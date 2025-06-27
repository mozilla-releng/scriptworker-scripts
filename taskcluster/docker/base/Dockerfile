# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

FROM ghcr.io/astral-sh/uv:0.7.15-bookworm
ARG PYTHON_VERSION

RUN ln -s /app/docker.d/healthcheck /bin/healthcheck \
 && groupadd --gid 10001 app \
 && useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

# %include scriptworker_client
ADD --chown=app:app topsrcdir/scriptworker_client /app/scriptworker_client
# %include configloader
ADD --chown=app:app topsrcdir/configloader /app/configloader
# %include docker.d
ADD --chown=app:app topsrcdir/docker.d /app/docker.d
# %include .dockerignore
ADD --chown=app:app topsrcdir/.dockerignore /app/.dockerignore

USER app
WORKDIR /app

# Install scriptworker_client and configloader
RUN uv venv --python ${PYTHON_VERSION} /app/.venv \
 && . /app/.venv/bin/activate \
 && cd /app/scriptworker_client \
 && uv pip install . \
 && deactivate \
 && uv venv /app/configloader_venv \
 && . /app/configloader_venv/bin/activate \
 && cd /app/configloader \
 && uv pip install . \
 && deactivate

CMD ["/app/docker.d/init.sh"]
