import logging
import os
import shutil
import tempfile

from scriptworker.utils import makedirs

from pushsnapscript import task
from pushsnapscript.utils import cwd

# XXX Hack to only import a subset of snapcraft. Otherwise snapcraft can't be built on any other
# distribution than Ubuntu. The prod instance runs CentOS 6. There isn't a package version of
# snapcraft on that platform either.
import sys
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(dir_path, 'snapcraft'))
from snapcraft import _store as snapcraft_store_client  # noqa

log = logging.getLogger(__name__)


def push(context, snap_file_path, channel):
    if not task.is_allowed_to_push_to_snap_store(channel=channel):
        log.warn('Not allowed to push to Snap store. Skipping push...')
        # We don't raise an error because we still want green tasks on dev instances
        return

    # Snapcraft requires credentials to be stored at $CWD/.snapcraft/snapcraft.cfg. Let's store them
    # in a folder that gets purged at the end of the run.
    with tempfile.TemporaryDirectory() as temp_dir:
        _craft_credentials_file(context, channel, temp_dir)

        log.debug('Calling snapcraft push with these args: {}, {}'.format(snap_file_path, channel))
        with cwd(temp_dir):
            snapcraft_store_client.push(snap_file_path, channel)


def _craft_credentials_file(context, channel, temp_dir):
    macaroon_original_location = context.config['macaroons_locations'][channel]

    snapcraft_dir = os.path.join(temp_dir, '.snapcraft')
    makedirs(snapcraft_dir)
    macaroon_target_location = os.path.join(snapcraft_dir, 'snapcraft.cfg')
    shutil.copyfile(macaroon_original_location, macaroon_target_location)
