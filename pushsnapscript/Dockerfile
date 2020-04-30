FROM python:3.8

RUN groupadd --gid 10001 app && \
    useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

RUN apt-get update \
 && apt-get install -y libsodium-dev \
 && apt-get install -y squashfs-tools \
 && apt-get install -y xdelta3 \
 && apt-get clean \
 # XXX Avoid snapcraft from loading useless libs when running on Ubuntu
 && truncate -s 0 /etc/os-release \
 && ln -s /app/docker.d/healthcheck /bin/healthcheck

USER app
WORKDIR /app

COPY . /app

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
