import aiohttp
import hashlib
import humanize
import logging
import os
import requests

from mozilla_version.gecko import FennecVersion

logger = logging.getLogger(__name__)


def load_json_url(url):
    return requests.get(url).json()


async def download_file(session: aiohttp.ClientSession, url, local_file_path):
    async with session.get(url, raise_for_status=True) as response:
        logger.info('Downloading... {} ({}) to "{}"'
                    .format(url, humanize.naturalsize(response.headers['content-length']), local_file_path))
        with open(local_file_path, 'wb') as f:
            f.write(await response.read())
            logger.info('Downloaded "{}"'.format(os.path.basename(local_file_path)))


def file_sha512sum(file_path):
    bs = 65536
    hasher = hashlib.sha512()
    with open(file_path, 'rb') as fh:
        buf = fh.read(bs)
        while len(buf) > 0:
            hasher.update(buf)
            buf = fh.read(bs)
    return hasher.hexdigest()


def filter_out_identical_values(list_):
    return list(set(list_))


def is_firefox_version_nightly(firefox_version):
    version = FennecVersion.parse(firefox_version)
    if not (version.is_nightly or version.is_beta or version.is_release):
        raise ValueError('Unsupported version: {}'.format(firefox_version))

    return version.is_nightly


def add_push_arguments(parser):
    parser.add_argument('--secret', required=True,
                        help='File that contains google credentials (json)')
    parser.add_argument('--do-not-contact-server', action='store_false', dest='contact_server',
                        help='''Prevent any request to reach the APK server. Use this option if
you want to run the script without any valid credentials nor valid APKs. --credentials must
still be provided (you can pass a random file name).''')
    parser.add_argument('track', help='Track on which to upload')
    parser.add_argument(
        '--rollout-percentage',
        type=int,
        choices=range(0, 101),
        metavar='[0-100]',
        default=None,
        help='The percentage of user who will get the update. Specify only if track is rollout'
    )
    parser.add_argument('--commit', action='store_false', dest='dry_run',
                        help='Commit new release on Google Play. This action cannot be reverted')


def metadata_by_package_name(metadata_dict):
    package_names = {}
    for (file, metadata) in metadata_dict.items():
        package_name = metadata['package_name']
        if package_name not in package_names:
            package_names[package_name] = []
        package_names[package_name].append((file, metadata))

    return package_names
