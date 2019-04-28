ARG PYTHON_VERSION=3.7
FROM python:${PYTHON_VERSION}-slim

RUN groupadd --gid 10001 app && \
    useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

USER app
WORKDIR /app

RUN python -m venv /app
COPY ./ ./
RUN ./bin/pip install -r requirements-prod.txt
RUN ./bin/pip install -e .
RUN ./bin/pip install https://github.com/rail/configloader/archive/f5ce2db480fd159af77e1927dbd595abc7412163.tar.gz
COPY docker.d/healthcheck /bin/healthcheck
COPY docker.d/init.sh /app/bin/init.sh

# TODO: generate /app/version.json according to https://github.com/mozilla-services/Dockerflow/blob/master/docs/version_object.md

CMD ["/app/bin/init.sh"]
