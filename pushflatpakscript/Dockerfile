FROM python:3.11.9

RUN groupadd --gid 10001 app && \
    useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

RUN ln -s /app/docker.d/healthcheck /bin/healthcheck

WORKDIR /app
COPY . /app

RUN /app/docker.d/image_setup.sh

USER app

RUN python -m venv /app \
 && cd pushflatpakscript \
 && /app/bin/pip install --no-deps -r requirements/base.txt \
 && /app/bin/pip install . \
 && python -m venv /app/configloader_venv \
 && cd /app/configloader \
 && /app/configloader_venv/bin/pip install --no-deps -r requirements/base.txt \
 && /app/configloader_venv/bin/pip install . \
 && python -m venv /app/flat_manager_venv \
 && /app/flat_manager_venv/bin/pip install --no-deps -r /app/pushflatpakscript/requirements/flat-manager.txt \
 && curl -Ls \
    https://github.com/flatpak/flat-manager/raw/100d44f761ba765552d2a799b5b7254b6a8b1e38/flat-manager-client | \
    sed -e '1i#!/app/flat_manager_venv/bin/python' -e '1d' > /app/flat_manager_venv/bin/flat-manager-client \
 && chmod 755 /app/flat_manager_venv/bin/flat-manager-client \
 && echo "2e55c0d3797f948b5b2eb86b897d42ce318b829749a23b903d8a9ed7b3bcea59 /app/flat_manager_venv/bin/flat-manager-client" | sha256sum -c \
 && cd /app


CMD ["/app/docker.d/init.sh"]
