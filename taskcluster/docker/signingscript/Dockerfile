# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

FROM $DOCKER_IMAGE_PARENT AS makemsix

USER root

RUN apt-get update \
 && apt-get install --no-install-recommends -y cmake make clang git libicu-dev \
 && apt-get clean

ADD topsrcdir/signingscript/docker.d/build_msix_packaging.sh /app/msix-packaging/build_msix_packaging.sh

# Build makemsix
RUN cd /app/msix-packaging && bash build_msix_packaging.sh

FROM $DOCKER_IMAGE_PARENT

# %include signingscript
ADD --chown=app:app topsrcdir/signingscript /app/signingscript

# %include vendored
ADD --chown=app:app topsrcdir/vendored /app/vendored

# Root for installs
USER root

# Install msix
COPY --from=makemsix /app/msix-packaging/msix-packaging/.vs/bin/makemsix /usr/bin/makemsix
COPY --from=makemsix /app/msix-packaging/msix-packaging/.vs/lib/libmsix.so /usr/lib/libmsix.so

# Install system dependencies and rcodesign
RUN apt-get update \
 && apt-get install --no-install-recommends -y osslsigncode gpg gpgv wget libicu76 \
 && apt-get clean \
 && wget -qO- \
    https://github.com/indygreg/apple-platform-rs/releases/download/apple-codesign%2F0.29.0/apple-codesign-0.29.0-x86_64-unknown-linux-musl.tar.gz \
    | tar xvz -C /usr/bin --transform 's/.*\///g' --wildcards --no-anchored 'rcodesign' \
 && chmod +x /usr/bin/rcodesign

# Ensure makemsix minimally works (e.g. no missing libs)
RUN makemsix -?

# Set user and workdir
USER app
WORKDIR /app

# Install signingscript + widevine
RUN cp -R /app/signingscript/docker.d/* /app/docker.d/ \
 && . /app/.venv/bin/activate \
 && uv sync --no-dev --active --frozen --package signingscript \
 && ln -sf /etc/widevine.py $(/app/.venv/bin/python -c "import site; print(site.getsitepackages()[0])")/widevine.py
