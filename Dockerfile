FROM python:3.7

RUN groupadd --gid 10001 app && \
    useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

USER app
WORKDIR /app

COPY . /app

RUN python -m venv /app
RUN ./bin/pip install -r requirements-dev.txt
RUN ./bin/pip install -e .
RUN ./bin/pip install https://github.com/rail/configloader/archive/d0336ed42f364ae5da749851d855ada1d6ff9951.tar.gz

COPY docker.d/healthcheck /bin/healthcheck
COPY docker.d/init.sh /app/bin/init.sh

CMD ["/app/bin/init.sh"]
