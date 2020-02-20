FROM python:3.8

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
 && python -m venv /app/configloader_venv \
 && cd /app/configloader \
 && /app/configloader_venv/bin/pip install -r requirements/base.txt \
 && /app/configloader_venv/bin/pip install . \
 && ln -sf /etc/widevine.py $(/app/bin/python -c "import site; print(site.getsitepackages()[0])")/widevine.py \
 && cd /app

CMD ["/app/docker.d/init.sh"]
