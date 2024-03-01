# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

FROM $DOCKER_IMAGE_PARENT

# %include pushapkscript
ADD --chown=app:app topsrcdir/pushapkscript /app/pushapkscript

USER root
RUN apt-get update \
 && apt-get install -y default-jdk \
 && apt-get clean

USER app

RUN cp -R /app/pushapkscript/docker.d/* /app/docker.d/ \
 && python -m venv /app \
 && cd pushapkscript \
 && /app/bin/pip install -r requirements/base.txt \
 && /app/bin/pip install . \
 && python -m venv /app/configloader_venv \
 && cd /app/configloader \
 && /app/configloader_venv/bin/pip install -r requirements/base.txt \
 && /app/configloader_venv/bin/pip install . \
 && cd /app \
 && curl -L https://github.com/google/bundletool/releases/download/1.15.4/bundletool-all-1.15.4.jar -o /app/bundletool.jar \
 && echo "e5f54597dbb5211f050e8ddd03d4d731a9b4dfa5684c7687928b654a8ddc212a bundletool.jar" > shasum \
 && sha256sum --check --status shasum

ENV BUNDLETOOL_PATH=/app/bundletool.jar
