ARG BASE_IMAGE
FROM $BASE_IMAGE

RUN ln -s /app/docker.d/healthcheck /bin/healthcheck

RUN groupadd --gid 10001 app \
  && useradd -g app --uid 10001 --shell /usr/sbin/nologin --create-home --home-dir /app app

# %include scriptworker_client
ADD topsrcdir/scriptworker_client /app/scriptworker_client
# %include configloader
ADD topsrcdir/configloader /app/configloader
# %include docker.d
ADD topsrcdir/docker.d /app/docker.d

# Replace all permissions on copied files
RUN chown -R app:app /app

USER app
WORKDIR /app

CMD ["/app/docker.d/init.sh"]
