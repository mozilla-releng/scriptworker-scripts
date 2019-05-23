FROM python:3.7

RUN groupadd --gid 10001 app && \
    useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

USER app
WORKDIR /app

COPY . /app
# generate /app/version.json according to https://github.com/mozilla-services/Dockerflow/blob/master/docs/version_object.md
RUN cd /app && /app/docker.d/generate_version_json.sh

RUN python -m venv /app
RUN ./bin/pip install -r requirements.txt
RUN ./bin/pip install -e .
RUN ./bin/pip install https://github.com/rail/configloader/archive/edc1fc846e225e5dc1c35070ab68f336a10596f2.tar.gz

COPY docker.d/healthcheck /bin/healthcheck
COPY docker.d/init.sh /app/bin/init.sh

CMD ["/app/bin/init.sh"]
