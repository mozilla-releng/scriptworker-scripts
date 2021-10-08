# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# We need to run a really old docker version because taskcluster is using a
# really old version in their setup
FROM docker:1.6.2@sha256:9089ceab1cf3fe5e23713a7f05732f45cbd773818c57042ae065c3dffaef9b54

RUN apk add --update xz
RUN mkdir -p /usr/local/bin
COPY build_and_push.sh /usr/local/bin/build_and_push.sh

# Add worker user
RUN mkdir /builds && \
    adduser -D -h /builds/worker -g worker -u 1000 worker && \
    mkdir /builds/worker/artifacts && \
    chown worker:worker /builds/worker/artifacts

ENV SHELL=/bin/sh \
    HOME=/builds/worker \
    PATH=/builds/worker/.local/bin:$PATH

VOLUME /builds/worker/checkouts
VOLUME /builds/worker/.cache

# Set a default command useful for debugging
CMD ["/bin/sh"]
