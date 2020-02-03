FROM python:3.7

RUN groupadd --gid 10001 app && \
    useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

RUN apt-get update \
 && apt-get install -y mercurial \
 && apt-get clean \
 && ln -s /app/docker.d/healthcheck /bin/healthcheck

USER app
WORKDIR /app

COPY . /app

RUN python -m venv /app \
 && cd /app/scriptworker_client \
 && /app/bin/pip install -r requirements/base.txt \
 && /app/bin/pip install . \
 && cd /app/treescript \
 && /app/bin/pip install -r requirements/base.txt \
 && /app/bin/pip install . \
 && python -m venv /app/configloader_venv \
 && cd /app/configloader \
 && /app/configloader_venv/bin/pip install -r requirements/base.txt \
 && /app/configloader_venv/bin/pip install . \
 && cd /app \
 && hg clone -r d47591074dc0d44a0b9e0838ce790db528cbd534 https://hg.mozilla.org/hgcustom/version-control-tools /app/version-control-tools \
 && cp /app/treescript/data/hgrc /etc/mercurial/hgrc.d/treescript.rc

COPY docker.d/extensions.rc /etc/mercurial/hgrc.d/extensions.rc

CMD ["/app/docker.d/init.sh"]
