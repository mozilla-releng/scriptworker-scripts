import contextlib
import logging
import os

from pushsnapscript import task

# XXX Hack to only import a subset of snapcraft. Otherwise snapcraft can't be built on any other
# distribution than Ubuntu. The prod instance runs CentOS 6. There isn't a package version of
# snapcraft on that platform either.
import sys
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(dir_path, 'snapcraft'))
from snapcraft import _store as snapcraft_store_client  # noqa
from snapcraft import storeapi                          # noqa

log = logging.getLogger(__name__)


def push(context, snap_file_path, channel):
    if not task.is_allowed_to_push_to_snap_store(channel=channel):
        log.warn('Not allowed to push to Snap store. Skipping push...')
        # We don't raise an error because we still want green tasks on dev instances
        return

    macaroon_location = context.config['macaroons_locations'][channel]
    with _session(macaroon_location):
        push_kwargs = {
            'snap_filename': snap_file_path,
            'release_channels': [channel],
        }
        log.debug('Calling snapcraft push with these kwargs: {}'.format(push_kwargs))
        snapcraft_store_client.push(**push_kwargs)


@contextlib.contextmanager
def _session(macaroon_location):
    store = storeapi.StoreClient()

    with open(macaroon_location) as macaroon:
        log.debug('Logging onto Snap store with macaroon file "{}"...'.format(macaroon.name))
        snapcraft_store_client.login(store=store, config_fd=macaroon)

    log.info('Logged on Snap store')
    try:
        yield
    finally:
        log.debug('Logging off Snap store...')
        store.logout()
        log.info('Logged off Snap store')
