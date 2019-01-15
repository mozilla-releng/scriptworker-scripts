import aiohttp
import hashlib
import humanize
import logging
import os
import requests
from enum import Enum

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


class PRODUCT(Enum):
    KLAR = "org.mozilla.klar"
    FENIX = "org.mozilla.fenix"
    FOCUS = "org.mozilla.focus"
    REFERENCE_BROWSER = "org.mozilla.reference.browser"

    @staticmethod
    def get_value_or_none(value):
        return PRODUCT(value) if PRODUCT.contains_value(value) else None

    @staticmethod
    def contains_value(value):
        return any([value == item.value for item in PRODUCT])

    @staticmethod
    def is_focus_flavor(value):
        return PRODUCT.contains_value(value) and (PRODUCT(value) == PRODUCT.FOCUS or PRODUCT(value) == PRODUCT.KLAR)

    @staticmethod
    def is_fenix(value):
        return PRODUCT.contains_value(value) and PRODUCT(value) == PRODUCT.FENIX

    @staticmethod
    def is_reference_browser(value):
        return PRODUCT.contains_value(value) and PRODUCT(value) == PRODUCT.REFERENCE_BROWSER


def get_firefox_package_name(firefox_version):
    version = FennecVersion.parse(firefox_version)
    if version.is_nightly:
        return 'org.mozilla.fennec_aurora'
    elif version.is_beta:
        return 'org.mozilla.firefox_beta'
    elif version.is_release:
        return 'org.mozilla.firefox'
    else:
        raise ValueError('Unsupported version: {}'.format(firefox_version))
