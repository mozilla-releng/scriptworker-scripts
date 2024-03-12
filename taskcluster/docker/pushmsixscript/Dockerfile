# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

FROM $DOCKER_IMAGE_PARENT

# %include pushmsixscript
ADD --chown=app:app topsrcdir/pushmsixscript /app/pushmsixscript

RUN cp -R /app/pushmsixscript/docker.d/* /app/docker.d/ \
 && python -m venv /app \
 && cd /app/scriptworker_client \
 && /app/bin/pip install --no-deps -r requirements/base.txt \
 && /app/bin/pip install . \
 && cd /app/pushmsixscript \
 && /app/bin/pip install --no-deps -r requirements/base.txt \
 && /app/bin/pip install . \
 && python -m venv /app/configloader_venv \
 && cd /app/configloader \
 && /app/configloader_venv/bin/pip install --no-deps -r requirements/base.txt \
 && /app/configloader_venv/bin/pip install .
