FROM python:3.7

RUN groupadd --gid 10001 app && \
    useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

RUN apt-get update \
 && apt-get install -y default-jdk \
 && apt-get clean \
 && ln -s /app/docker.d/healthcheck /bin/healthcheck

USER app
WORKDIR /app

COPY . /app

RUN python -m venv /app \
 && ./bin/pip install -r requirements/base.txt \
 && ./bin/pip install -e . \
 && ./bin/pip install -r /app/docker.d/configloader/requirements/base.txt \
 && ./bin/pip install /app/docker.d/configloader

CMD ["/app/docker.d/init.sh"]
