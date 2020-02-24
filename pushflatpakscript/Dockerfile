FROM python:3.8

RUN groupadd --gid 10001 app && \
    useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

RUN apt-get update \
 && apt-get install -y gir1.2-ostree-1.0 libgirepository1.0-dev \
 && apt-get clean \
 && ln -s /app/docker.d/healthcheck /bin/healthcheck

USER app
WORKDIR /app

COPY . /app

RUN python -m venv /app \
 && ./bin/pip install --upgrade pip \
 && cd pushsnapscript \
 && /app/bin/pip install -r requirements/base.txt \
 && /app/bin/pip install . \
 && python -m venv /app/configloader_venv \
 && cd /app/configloader \
 && /app/configloader_venv/bin/pip install -r requirements/base.txt \
 && /app/configloader_venv/bin/pip install . \
 && cd /app

RUN curl -O /app/bin/flat-manager-client \
 https://raw.githubusercontent.com/flatpak/flat-manager/a0005a8046a290590ccb53b631b9949ba52fd8cd/flat-manager-client \
 && chmod 755 /app/bin/flat-manager-client

CMD ["/app/docker.d/init.sh"]
