# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

FROM $DOCKER_IMAGE_PARENT

# %ARG SCRIPT_NAME
# %include $SCRIPT_NAME
ADD --chown=app:app topsrcdir/$SCRIPT_NAME /app/$SCRIPT_NAME

RUN ([ -d /app/$SCRIPT_NAME/docker.d ] && cp -R /app/$SCRIPT_NAME/docker.d/* /app/docker.d/) \
 && . /app/.venv/bin/activate \
 &&  uv sync --no-dev --active --frozen --package $SCRIPT_NAME
