# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

ARG BASE_IMAGE
FROM $BASE_IMAGE

RUN ln -s /app/docker.d/healthcheck /bin/healthcheck

RUN groupadd --gid 10001 app \
  && useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

# %include scriptworker_client
ADD --chown=app:app topsrcdir/scriptworker_client /app/scriptworker_client
# %include configloader
ADD --chown=app:app topsrcdir/configloader /app/configloader
# %include docker.d
ADD --chown=app:app topsrcdir/docker.d /app/docker.d

USER app
WORKDIR /app

CMD ["/app/docker.d/init.sh"]
