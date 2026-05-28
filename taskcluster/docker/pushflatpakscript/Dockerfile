# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

FROM $DOCKER_IMAGE_PARENT AS flat_manager

USER root
RUN apt-get update && apt-get install --no-install-recommends -y curl \
 && curl -fLo /flat-manager-client --retry 5 --retry-delay 10 \
    https://github.com/flatpak/flat-manager/releases/download/0.5.0/flat-manager-client.amd64 \
 && echo "9733a148ac185bc8d7fb0429a43f9ad7d934635760bb71933658642c697f87c9  /flat-manager-client" | sha256sum -c \
 && chmod 755 /flat-manager-client

FROM $DOCKER_IMAGE_PARENT

# %include pushflatpakscript
ADD --chown=app:app topsrcdir/pushflatpakscript /app/pushflatpakscript

USER root
RUN /app/pushflatpakscript/docker.d/image_setup.sh

USER app

RUN cp -R /app/pushflatpakscript/docker.d/* /app/docker.d/ \
 && . /app/.venv/bin/activate \
 && uv sync --no-dev --active --frozen --package pushflatpakscript

COPY --from=flat_manager /flat-manager-client /app/bin/flat-manager-client

# Ensure flat-manager-client minimally works (e.g. no missing libs)
RUN /app/bin/flat-manager-client --help
