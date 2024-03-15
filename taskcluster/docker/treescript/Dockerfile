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
 && python -m venv /app \
 && cd /app/scriptworker_client \
 && /app/bin/pip install -r requirements/base.txt \
 && /app/bin/pip install . \
 && cd /app/treescript \
 && /app/bin/pip install -r requirements/base.txt \
 && /app/bin/pip install . \
 && python -m venv /app/configloader_venv \
 && cd /app/configloader \
 && /app/configloader_venv/bin/pip install -r requirements/base.txt \
 && /app/configloader_venv/bin/pip install . \
 && cd /app \
 && hg clone -r 0180a71f29b2f71113665cf9425fd73693d0265c https://hg.mozilla.org/hgcustom/version-control-tools /app/version-control-tools
