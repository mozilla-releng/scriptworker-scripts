ARG PYTHON_VERSION=3.7
FROM python:${PYTHON_VERSION}-slim

RUN groupadd --gid 10001 app && \
    useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app


COPY --chown=10001:10001 . /app

# generate /app/version.json according to https://github.com/mozilla-services/Dockerflow/blob/master/docs/version_object.md
RUN apt-get update && apt-get -yq install git && \
    cd /app && /app/docker.d/generate_version_json.sh && \
    apt-get remove -yq git && \
    apt-get autoremove -yq && \
    apt-get clean

USER app
WORKDIR /app

RUN python -m venv /app
RUN ./bin/pip install -r requirements-dev.txt
RUN ./bin/pip install -e .
RUN ./bin/pip install https://github.com/rail/configloader/archive/f5ce2db480fd159af77e1927dbd595abc7412163.tar.gz

COPY docker.d/healthcheck /bin/healthcheck
COPY docker.d/init.sh /app/bin/init.sh

CMD ["/app/bin/init.sh"]
