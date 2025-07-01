# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

FROM $DOCKER_IMAGE_PARENT

# %include treescript
ADD --chown=app:app topsrcdir/treescript /app/treescript

USER root
RUN apt-get update \
 && apt-get install -y mercurial \
 && apt-get clean \
 && cp /app/treescript/src/treescript/data/hgrc /etc/mercurial/hgrc.d/treescript.rc \
 && cp /app/treescript/docker.d/extensions.rc /etc/mercurial/hgrc.d/extensions.rc

USER app
WORKDIR /app

RUN cp -R /app/treescript/docker.d/* /app/docker.d/ \
 && . /app/.venv/bin/activate \
 && cd /app/treescript \
 && uv pip install . \
 && cd /app \
 && hg clone -r 90302f015ac8dd8877ef3ee24b5a62541142378b https://hg.mozilla.org/hgcustom/version-control-tools /app/version-control-tools
