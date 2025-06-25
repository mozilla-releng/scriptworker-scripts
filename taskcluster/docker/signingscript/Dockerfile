# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

FROM $DOCKER_IMAGE_PARENT

# %include signingscript
ADD --chown=app:app topsrcdir/signingscript /app/signingscript

# %include vendored
ADD --chown=app:app topsrcdir/vendored /app/vendored

# Root for installs
USER root

# Install msix
# Install rcodesign
RUN apt-get update \
 && apt-get install -y osslsigncode cmake clang \
 && apt-get clean \
 && chown -R app:app /app \
 && cd /app/signingscript/docker.d \
 && bash build_msix_packaging.sh \
 && cp msix-packaging/.vs/bin/makemsix /usr/bin \
 && cp msix-packaging/.vs/lib/libmsix.so /usr/lib \
 && cd .. \
 && rm -rf msix-packaging \
 && wget -qO- \
    https://github.com/indygreg/apple-platform-rs/releases/download/apple-codesign%2F0.29.0/apple-codesign-0.29.0-x86_64-unknown-linux-musl.tar.gz \
    | tar xvz -C /usr/bin --transform 's/.*\///g' --wildcards --no-anchored 'rcodesign' \
 && chmod +x /usr/bin/rcodesign

# Set user and workdir
USER app
WORKDIR /app

# Install signingscript + widevine
RUN cp -R /app/signingscript/docker.d/* /app/docker.d/ \
 && . /app/.venv/bin/activate \
 && cd /app/vendored/mozbuild \
 && uv pip install . \
 && cd /app/signingscript \
 && uv pip install . \
 && ln -sf /etc/widevine.py $(/app/.venv/bin/python -c "import site; print(site.getsitepackages()[0])")/widevine.py
