FROM python:3.9.7

RUN groupadd --gid 10001 app && \
    useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

COPY ["githubscript", "/app/githubscript/"]
COPY ["scriptworker_client", "/app/scriptworker_client/"]
COPY ["configloader", "/app/configloader/"]
COPY ["docker.d", "/app/docker.d/"]

RUN chown -R app:app /app && \
    ln -s /app/docker.d/healthcheck /bin/healthcheck

WORKDIR /app
USER app

RUN python -m venv /app \
 && cd /app/scriptworker_client \
 && /app/bin/pip install -r requirements/base.txt \
 && /app/bin/pip install . \
 && cd /app/githubscript \
 && /app/bin/pip install -r requirements/base.txt \
 && /app/bin/pip install . \
 && python -m venv /app/configloader_venv \
 && cd /app/configloader \
 && /app/configloader_venv/bin/pip install -r requirements/base.txt \
 && /app/configloader_venv/bin/pip install . \
 && cd /app

CMD ["/app/docker.d/init.sh"]
