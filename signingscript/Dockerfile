# python:3.9.7 docker image contains osslsigncode 2.1.0.
# if the image changes, verify version of osslsigncode and make sure winsign works as well
FROM python:3.9.7

RUN groupadd --gid 10001 app && \
    useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app && \
    apt-get update && \
    apt-get install -y osslsigncode cmake clang && \
    apt-get clean && \
    ln -s /app/docker.d/healthcheck /bin/healthcheck

# Copy only required folders
COPY ["signingscript", "/app/signingscript/"]
COPY ["scriptworker_client", "/app/scriptworker_client/"]
COPY ["configloader", "/app/configloader/"]
COPY ["docker.d", "/app/docker.d/"]
COPY ["vendored", "/app/vendored/"]

# Copy the version.json file if it's present
COPY ["version.jso[n]", "/app/"]

# Change owner of /app to app:app
# Build and install libdmg_hfsplus
# Install msix
# Install rcodesign
RUN chown -R app:app /app \
 && cd /app/signingscript/docker.d \
 && bash build_libdmg_hfsplus.sh /usr/bin \
 && bash install_rcodesign.sh /usr/bin \
 && bash build_msix_packaging.sh

# Set user and workdir
USER app
WORKDIR /app

# Install signingscript + configloader + widevine
RUN python -m venv /app \
 && /app/bin/pip install /app/scriptworker_client \
 && cd signingscript \
 && /app/bin/pip install -r requirements/base.txt \
 && /app/bin/pip install . \
 && python -m venv /app/configloader_venv \
 && cd /app/configloader \
 && /app/configloader_venv/bin/pip install -r requirements/base.txt \
 && /app/configloader_venv/bin/pip install . \
 && ln -sf /etc/widevine.py $(/app/bin/python -c "import site; print(site.getsitepackages()[0])")/widevine.py \
 && cd /app

CMD ["/app/docker.d/init.sh"]
