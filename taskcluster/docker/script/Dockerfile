# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

FROM $DOCKER_IMAGE_PARENT

# %ARG SCRIPT_NAME
# %include $SCRIPT_NAME
ADD --chown=app:app topsrcdir/$SCRIPT_NAME /app/$SCRIPT_NAME

RUN cd /app/$SCRIPT_NAME \
 && ([ -d docker.d ] && cp -R docker.d/* /app/docker.d/) \
 && /app/bin/pip install -r requirements/base.txt \
 && /app/bin/pip install .
