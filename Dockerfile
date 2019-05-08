ARG PYTHON_VERSION=3.7
ARG TASK_GROUP_ID
FROM python:${PYTHON_VERSION}

RUN groupadd --gid 10001 app && \
    useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

COPY --chown=10001:10001 . /app

# generate /app/version.json according to https://github.com/mozilla-services/Dockerflow/blob/master/docs/version_object.md
RUN cd /app && TASK_GROUP_ID=$TASK_GROUP_ID /app/docker.d/generate_version_json.sh

USER app
WORKDIR /app

RUN python -m venv /app
RUN ./bin/pip install -r requirements-dev.txt
RUN ./bin/pip install -e .
RUN ./bin/pip install https://github.com/rail/configloader/archive/edc1fc846e225e5dc1c35070ab68f336a10596f2.tar.gz

COPY docker.d/healthcheck /bin/healthcheck
COPY docker.d/init.sh /app/bin/init.sh

CMD ["/app/bin/init.sh"]
