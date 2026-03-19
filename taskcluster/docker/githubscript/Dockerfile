# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

FROM $DOCKER_IMAGE_PARENT

USER root

# We use mimetypes.guess_type which depends on /etc/mime.types
RUN apt-get update && apt-get install -y --no-install-recommends media-types && apt-get clean

USER app

# %include githubscript
ADD --chown=app:app topsrcdir/githubscript /app/githubscript

RUN cp -R /app/githubscript/docker.d/* /app/docker.d/ \
 && . /app/.venv/bin/activate \
 &&  uv sync --no-dev --active --frozen --package githubscript
