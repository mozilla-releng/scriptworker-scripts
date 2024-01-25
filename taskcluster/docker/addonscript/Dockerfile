FROM $DOCKER_IMAGE_PARENT

# %include addonscript
ADD topsrcdir/addonscript /app/addonscript

RUN cp /app/addonscript/docker.d/* /app/docker.d \
 && python -m venv /app \
 && cd addonscript \
 && /app/bin/pip install -r requirements/base.txt \
 && /app/bin/pip install . \
 && python -m venv /app/configloader_venv \
 && cd /app/configloader \
 && /app/configloader_venv/bin/pip install -r requirements/base.txt \
 && /app/configloader_venv/bin/pip install .
