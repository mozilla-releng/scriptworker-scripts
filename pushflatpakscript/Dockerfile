FROM python:3.8@sha256:037c262134bc0cffa81606421308eb0dbf5c851c2328ec585983f8c18553966f

RUN groupadd --gid 10001 app && \
    useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

RUN ln -s /app/docker.d/healthcheck /bin/healthcheck

WORKDIR /app
COPY . /app

RUN /app/docker.d/image_setup.sh

USER app

RUN python -m venv /app \
 && cd pushflatpakscript \
 && /app/bin/pip install -r requirements/base.txt \
 && /app/bin/pip install . \
 && python -m venv /app/configloader_venv \
 && cd /app/configloader \
 && /app/configloader_venv/bin/pip install -r requirements/base.txt \
 && /app/configloader_venv/bin/pip install . \
 && python -m venv /app/flat_manager_venv \
 && /app/flat_manager_venv/bin/pip install -r /app/pushflatpakscript/requirements/flat-manager.txt \
 && curl -s \
    https://raw.githubusercontent.com/flatpak/flat-manager/a0005a8046a290590ccb53b631b9949ba52fd8cd/flat-manager-client | \
    sed -e '1i#!/app/flat_manager_venv/bin/python' -e '1d' > /app/flat_manager_venv/bin/flat-manager-client \
 && chmod 755 /app/flat_manager_venv/bin/flat-manager-client \
 && cd /app


CMD ["/app/docker.d/init.sh"]
