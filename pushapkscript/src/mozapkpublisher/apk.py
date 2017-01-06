import logging
import re

from io import BytesIO
from zipfile import ZipFile

from mozapkpublisher.exceptions import NoLocaleFound, NotMultiLocaleApk

logger = logging.getLogger(__name__)

_LOCALE_LINE_PATTERN = re.compile(r'^locale \S+ (\S+) .+')
_OMNI_JA_LOCATION = 'assets/omni.ja'
_CHROME_MANIFEST_LOCATION = 'chrome/chrome.manifest'


def check_if_apk_is_multilocale(apk_path):
    with ZipFile(apk_path) as apk_zip:
        omni_ja_data = BytesIO(apk_zip.read(_OMNI_JA_LOCATION))
        with ZipFile(omni_ja_data) as omni_ja:
            with omni_ja.open(_CHROME_MANIFEST_LOCATION) as manifest:
                manifest_raw_lines = manifest.readlines()

    unique_locales = _get_unique_locales(manifest_raw_lines)
    number_of_unique_locales = len(unique_locales)
    logger.info('"{}" contains {} locales: {}'.format(apk_path, number_of_unique_locales, unique_locales))

    if number_of_unique_locales == 0:
        raise NoLocaleFound(apk_path, _OMNI_JA_LOCATION, _CHROME_MANIFEST_LOCATION)
    elif number_of_unique_locales == 1:
        raise NotMultiLocaleApk(apk_path, unique_locales)


def _get_unique_locales(manifest_raw_lines):
    manifest_lines = [line.decode('utf-8') for line in manifest_raw_lines]

    locales = [
        _LOCALE_LINE_PATTERN.match(line).group(1) for line in manifest_lines
        if _LOCALE_LINE_PATTERN.match(line) is not None
    ]

    return list(set(locales))
