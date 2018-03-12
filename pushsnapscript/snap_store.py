import base64
import os

from scriptworker.utils import makedirs

from pushsnapscript.utils import cwd

# XXX Hack to only import a subset of snapcraft. Otherwise snapcraft can't be built on any other
# distribution than Ubuntu. The prod instance runs CentOS 6. There isn't a package version of
# snapcraft on that platform either.
import sys
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(dir_path, '..', 'snapcraft'))
from snapcraft import _store as snapcraft_store_client  # noqa


def push(context, snap_file_path, channel):
    # Snapcraft requires credentials to be stored at $CWD/.snapcraft/snapcraft.cfg. Let's store them
    # in a folder that gets purged at the end of the run.
    _craft_credentials_file(context, channel)
    with cwd(context.config['work_dir']):
        snapcraft_store_client.push(snap_file_path, channel)


def _craft_credentials_file(context, channel):
    base64_creds = context.config['base64_macaroons_configs'][channel]
    decoded_creds_bytes = base64.b64decode(base64_creds)
    decoded_creds = decoded_creds_bytes.decode()

    snapcraft_dir = os.path.join(context.config['work_dir'], '.snapcraft')
    makedirs(snapcraft_dir)
    snapcraft_config_file = os.path.join(snapcraft_dir, 'snapcraft.cfg')
    with open(snapcraft_config_file, 'w') as f:
        f.write(decoded_creds)
