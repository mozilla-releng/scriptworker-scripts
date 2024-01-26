# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

FROM $DOCKER_IMAGE_PARENT

# %include pushflatpakscript
ADD --chown=app:app topsrcdir/pushflatpakscript /app/pushflatpakscript

USER root
RUN apt-get update \
 && apt-get install -y gir1.2-ostree-1.0 libgirepository1.0-dev ostree \
 && apt-get clean

USER app

RUN python -m venv /app \
 && cd pushflatpakscript \
 && /app/bin/pip install -r requirements/base.txt \
 && /app/bin/pip install . \
 && python -m venv /app/configloader_venv \
 && cd /app/configloader \
 && /app/configloader_venv/bin/pip install -r requirements/base.txt \
 && /app/configloader_venv/bin/pip install . \
 && python -m venv /app/flat_manager_venv \
 && /app/flat_manager_venv/bin/pip install -r /app/pushflatpakscript/requirements/flat-manager.txt \
 && curl -Ls \
    https://github.com/flatpak/flat-manager/raw/d9d7972b24de6022c7079f8721fd8335c3319dc5/flat-manager-client | \
    sed -e '1i#!/app/flat_manager_venv/bin/python' -e '1d' > /app/flat_manager_venv/bin/flat-manager-client \
 && chmod 755 /app/flat_manager_venv/bin/flat-manager-client \
 && echo "5024c853d7529e82fc4a9fb9b982e561598df033545187238c9be8c791a6797c /app/flat_manager_venv/bin/flat-manager-client" | sha256sum -c
