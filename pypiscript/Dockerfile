FROM python:3.8

RUN groupadd --gid 10001 app && \
    useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

RUN ln -s /app/docker.d/healthcheck /bin/healthcheck

ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH=/usr/local/cargo/bin:$PATH \
    RUST_VERSION=1.42.0

RUN set -eux; \
    url="https://static.rust-lang.org/rustup/archive/1.21.1/x86_64-unknown-linux-gnu/rustup-init"; \
    wget "$url"; \
    echo "ad1f8b5199b3b9e231472ed7aa08d2e5d1d539198a15c5b1e53c746aad81d27b *rustup-init" | sha256sum -c -; \
    chmod +x rustup-init; \
    ./rustup-init -y --no-modify-path --profile minimal --default-toolchain $RUST_VERSION; \
    rm rustup-init; \
    chmod -R a+w $RUSTUP_HOME $CARGO_HOME; \
    rustup --version; \
    cargo --version; \
    rustc --version;

COPY . /app/
COPY pypiscript/docker.d/* /app/docker.d/
RUN chown -R app:app /app

USER app
WORKDIR /app

RUN python -m venv /app \
 && cd pypiscript \
 && /app/bin/pip install -r requirements/base.txt \
 && python -m venv /app/configloader_venv \
 && cd /app/configloader \
 && /app/configloader_venv/bin/pip install -r requirements/base.txt \
 && /app/configloader_venv/bin/pip install . \
 && cd /app \
 && cargo install --path pypiscript --root . \
 && mkdir /app/configs

RUN python -m pip install twine


CMD ["/app/docker.d/init.sh"]
