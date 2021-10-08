FROM python:3.8@sha256:037c262134bc0cffa81606421308eb0dbf5c851c2328ec585983f8c18553966f

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
 && hg clone -r 0180a71f29b2f71113665cf9425fd73693d0265c https://hg.mozilla.org/hgcustom/version-control-tools /app/version-control-tools

COPY treescript/src/treescript/data/hgrc /etc/mercurial/hgrc.d/treescript.rc
COPY treescript/docker.d/extensions.rc /etc/mercurial/hgrc.d/extensions.rc

CMD ["/app/docker.d/init.sh"]
