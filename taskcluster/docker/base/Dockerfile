# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

ARG PYTHON_VERSION
ARG UV_VERSION

FROM ghcr.io/astral-sh/uv:$UV_VERSION AS uv
FROM python:$PYTHON_VERSION

COPY --from=uv /uv /bin

RUN ln -s /app/docker.d/healthcheck /bin/healthcheck \
 && groupadd --gid 10001 app \
 && useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

COPY --from=scratch . /topsrcdir/

# %include scriptworker_client
# ADD --chown=app:app topsrcdir/scriptworker_client /app/scriptworker_client
# %include configloader
# ADD --chown=app:app topsrcdir/configloader /app/configloader
# %include docker.d
# ADD --chown=app:app topsrcdir/docker.d /app/docker.d
# %include .dockerignore
# ADD --chown=app:app topsrcdir/.dockerignore /app/.dockerignore
# %include uv.lock
# ADD --chown=app:app topsrcdir/uv.lock /app/uv.lock
# %include pyproject.toml
# ADD --chown=app:app topsrcdir/pyproject.toml /app/pyproject.toml

RUN cp -R /topsrcdir/* /app/ && chown -R app:app /app

USER app
WORKDIR /app

# Install configloader and create app venv
RUN uv venv /app/.venv \
 && uv venv /app/configloader_venv \
 && . /app/configloader_venv/bin/activate \
 &&  uv sync --no-dev --active --frozen --package configloader \
 && deactivate

CMD ["/app/docker.d/init.sh"]
