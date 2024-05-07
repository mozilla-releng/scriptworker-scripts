FROM python:3.9.7

RUN groupadd --gid 10001 app && \
    useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

RUN ln -s /app/docker.d/healthcheck /bin/healthcheck

WORKDIR /app

COPY . /app

# TODO: remove the pip upgrade when we upgrade to a base image with pip >= 23.3
RUN python -m venv /app \
 && cd beetmoverscript \
 && /app/bin/pip install --upgrade pip \
 && /app/bin/pip install --no-deps -r requirements/base.txt \
 && /app/bin/pip install . \
 && python -m venv /app/configloader_venv \
 && cd /app/configloader \
 && /app/configloader_venv/bin/pip install --no-deps -r requirements/base.txt \
 && /app/configloader_venv/bin/pip install .

USER app
CMD ["/app/docker.d/init.sh"]
