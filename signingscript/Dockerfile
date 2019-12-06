FROM python:3.7

RUN groupadd --gid 10001 app && \
    useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

RUN apt-get update \
 && apt-get install -y zipalign osslsigncode \
 && apt-get clean \
 && ln -s /app/docker.d/healthcheck /bin/healthcheck

COPY . /app
RUN chown -R app:app /app

USER app
WORKDIR /app

RUN python -m venv /app \
 && cd signingscript \
 && /app/bin/pip install -r requirements/base.txt \
 && /app/bin/pip install . \
 && cd /app/configloader \
 && /app/bin/pip install -r requirements/base.txt \
 && /app/bin/pip install . \
 && cd /app

CMD ["/app/docker.d/init.sh"]
