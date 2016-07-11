FROM ubuntu:xenial
MAINTAINER Francis Kang <fkang@mozilla.com>

# Required software
ENV DEBIAN_FRONTEND noninteractive
# Chain apt-get commands with apt-get clean in a single docker RUN
# to make sure that files are removed within a single docker layer
RUN rm /bin/sh && ln -s /bin/bash /bin/sh && \
    apt-get update -q && apt-get install -y software-properties-common && \
    apt-get install -yyq --no-install-recommends \
    python3.5 mercurial git curl python-cryptography virtualenv && \
    apt-get clean

RUN groupadd --gid 10001 app && \
    useradd --uid 10001 --gid 10001 --home /app --create-home app
USER app
COPY *.txt /app/
RUN virtualenv /app/py3.5 --python=/usr/bin/python3.5 && \
    source /app/py3.5/bin/activate && pip install -r /app/sw_requirements.txt
RUN virtualenv /app/py2 --python=/usr/bin/python --system-site-packages \
    && source /app/py2/bin/activate && \
    pip install -r /app/fbs_requirements.txt && deactivate

RUN hg clone https://hg.mozilla.org/build/tools /app/tools

COPY ./ /app
WORKDIR /app
ENTRYPOINT ["/app/py3.5/bin/scriptworker"]
CMD ["/app/config.json"]

ENV         HOME                        /app
ENV         SHELL                       /bin/bash
ENV         USER                        app
ENV         LOGNAME                     app

# ENVVARS for authentication
#ENV         TASKCLUSTER_CLIENT_ID       *clientId
#ENV         TASKCLUSTER_ACCESS_TOKEN    *AccessToken
#ENV         SCRIPTWORKER_WORKER_ID      *dummy-worker-francis3
#ENV         BALROG_API_ROOT             *not-balrog-vpn-proxy
#ENV         BALROG_USERNAME             *username
#ENV         BALROG_PASSWORD             *password
#ENV         S3_BUCKET                   *bucketwalrus
#ENV         AWS_ACCESS_KEY_ID           *awskeyid
#ENV         AWS_SECRET_ACCESS_KEY       *awssecret
