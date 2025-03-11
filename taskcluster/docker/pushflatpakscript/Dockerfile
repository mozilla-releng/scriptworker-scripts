# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

FROM $DOCKER_IMAGE_PARENT

# %include pushflatpakscript
ADD --chown=app:app topsrcdir/pushflatpakscript /app/pushflatpakscript

USER root
RUN /app/pushflatpakscript/docker.d/image_setup.sh

USER app

RUN cp -R /app/pushflatpakscript/docker.d/* /app/docker.d/ \
 && python -m venv /app \
 && cd pushflatpakscript \
 && /app/bin/pip install --no-deps -r requirements/base.txt \
 && /app/bin/pip install . \
 && python -m venv /app/configloader_venv \
 && cd /app/configloader \
 && /app/configloader_venv/bin/pip install --no-deps -r requirements/base.txt \
 && /app/configloader_venv/bin/pip install . \
 && python -m venv /app/flat_manager_venv \
 && /app/flat_manager_venv/bin/pip install --no-deps -r /app/pushflatpakscript/requirements/flat-manager.txt \
 && curl -Ls \
    https://github.com/flatpak/flat-manager/raw/100d44f761ba765552d2a799b5b7254b6a8b1e38/flat-manager-client | \
    sed -e '1i#!/app/flat_manager_venv/bin/python' -e '1d' > /app/flat_manager_venv/bin/flat-manager-client \
 && chmod 755 /app/flat_manager_venv/bin/flat-manager-client \
 && echo "2e55c0d3797f948b5b2eb86b897d42ce318b829749a23b903d8a9ed7b3bcea59 /app/flat_manager_venv/bin/flat-manager-client" | sha256sum -c
