# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

FROM $DOCKER_IMAGE_PARENT

# %include beetmoverscript
ADD --chown=app:app topsrcdir/beetmoverscript /app/beetmoverscript

# TODO: remove the pip upgrade when we upgrade to a base image with pip >= 23.3
RUN python -m venv /app \
 && cd /app/beetmoverscript \
 && /app/bin/pip install --upgrade pip \
 && /app/bin/pip install -r requirements/base.txt \
 && /app/bin/pip install . \
 && python -m venv /app/configloader_venv \
 && cd /app/configloader \
 && /app/configloader_venv/bin/pip install -r requirements/base.txt \
 && /app/configloader_venv/bin/pip install .
