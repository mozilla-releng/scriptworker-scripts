import logging
import re

from io import BytesIO
from zipfile import ZipFile

from mozapkpublisher.common.exceptions import NoLocaleFound, NotMultiLocaleApk, BadApk
from mozapkpublisher.common.utils import filter_out_identical_values

logger = logging.getLogger(__name__)

_LOCALE_LINE_PATTERN = re.compile(r'^locale \S+ (\S+) .+')
_OMNI_JA_LOCATION = 'assets/omni.ja'
_CHROME_MANIFEST_LOCATION = 'chrome/chrome.manifest'

_CLAIMED_ARCHITECTURE_PER_DIRECTORY_NAME = {
    'armeabi-v7a': 'armv7_v15',
    'x86': 'x86',
}
_DIRECTORY_WITH_ARCHITECTURE_METADATA = 'lib/'     # For instance: lib/x86/ or lib/armeabi-v7a/
_ARCHITECTURE_SUBDIRECTORY_INDEX = len(_DIRECTORY_WITH_ARCHITECTURE_METADATA.split('/')) - 1    # Removes last trailing slash


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


def check_if_apk_has_claimed_architecture(apk_path, architecture_name):
    architecture_within_apk = get_apk_architecture(apk_path)

    try:
        pretty_architecture_within_apk = _CLAIMED_ARCHITECTURE_PER_DIRECTORY_NAME[architecture_within_apk]
    except KeyError:
        raise BadApk('Architecture "{}" detected within APK, but it is not supported. Supported ones are: {}'.format(
            architecture_within_apk, _CLAIMED_ARCHITECTURE_PER_DIRECTORY_NAME.values()
        ))

    if pretty_architecture_within_apk != architecture_name:
        raise BadApk('"{}" is not built for the architecture called "{}". Detected architecture: {}'.format(
            apk_path, architecture_name, pretty_architecture_within_apk
        ))

    logger.info('"{}" is effectively built for architecture "{}"'.format(apk_path, architecture_name))


def get_apk_architecture(apk_path):
    with ZipFile(apk_path) as apk_zip:
        files_with_architecture_in_path = [
            file_info.filename for file_info in apk_zip.infolist()
            if _DIRECTORY_WITH_ARCHITECTURE_METADATA in file_info.filename
        ]

    if not files_with_architecture_in_path:
        raise BadApk('"{}" does not contain a directory called "{}"'
                     .format(apk_path, _DIRECTORY_WITH_ARCHITECTURE_METADATA))

    return _extract_architecture_from_paths(apk_path, files_with_architecture_in_path)


def _extract_architecture_from_paths(apk_path, paths):
    detected_architectures = [
        path.split('/')[_ARCHITECTURE_SUBDIRECTORY_INDEX] for path in paths
    ]
    unique_architectures = filter_out_identical_values(detected_architectures)
    non_empty_unique_architectures = [
        architecture for architecture in unique_architectures if architecture
    ]
    number_of_unique_architectures = len(non_empty_unique_architectures)

    if number_of_unique_architectures == 0:
        raise BadApk('"{}" does not contain any architecture data under these paths: {}'.format(apk_path, paths))
    elif number_of_unique_architectures > 1:
        raise BadApk('"{}" contains too many architures: {}'.format(apk_path, unique_architectures))

    return unique_architectures[0]
