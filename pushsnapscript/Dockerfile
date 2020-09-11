FROM python:3.8

RUN groupadd --gid 10001 app && \
    useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

RUN ln -s /app/docker.d/healthcheck /bin/healthcheck

WORKDIR /app
COPY . /app

# Production image requires extra packages
RUN /app/docker.d/image_setup.sh libsodium-dev squashfs-tools xdelta3

USER app

RUN python -m venv /app \
 && cd pushsnapscript \
 && /app/bin/pip install -r requirements/base.txt \
 && /app/bin/pip install . \
 && python -m venv /app/configloader_venv \
 && cd /app/configloader \
 && /app/configloader_venv/bin/pip install -r requirements/base.txt \
 && /app/configloader_venv/bin/pip install . \
 && cd /app

CMD ["/app/docker.d/init.sh"]
