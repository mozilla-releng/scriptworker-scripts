import codecs
import logging
import pyaxmlparser
import re
import shutil
import tempfile

from io import BytesIO
from zipfile import ZipFile


from mozapkpublisher.common.exceptions import BadApk, NoLocaleFound
from mozapkpublisher.common.utils import filter_out_identical_values

from configparser import ConfigParser


logger = logging.getLogger(__name__)


_DIRECTORY_WITH_ARCHITECTURE_METADATA = 'lib/'     # For instance: lib/x86/ or lib/armeabi-v7a/
_ARCHITECTURE_SUBDIRECTORY_INDEX = len(_DIRECTORY_WITH_ARCHITECTURE_METADATA.split('/')) - 1    # Removes last trailing slash

_LOCALE_LINE_PATTERN = re.compile(r'^locale \S+ (\S+) .+')
_OMNI_JA_LOCATION = 'assets/omni.ja'
_CHROME_MANIFEST_LOCATION = 'chrome/chrome.manifest'


def extract_metadata(original_apk_path, extract_architecture_metadata, extract_locale_metadata,
                     extract_firefox_metadata):
    logger.info('Extracting metadata from a copy of "{}"...'.format(original_apk_path))
    metadata = {}

    # We make a copy so a potentially malicious library doesn't stain the real APK
    with tempfile.NamedTemporaryFile() as apk_copy:
        shutil.copy(original_apk_path, apk_copy.name)
        apk_copy.seek(0)

        parsed_apk = pyaxmlparser.APK(apk_copy.name)
        package_name = parsed_apk.get_package()
        metadata['package_name'] = package_name
        metadata['api_level'] = int(parsed_apk.get_min_sdk_version())
        metadata['version_code'] = parsed_apk.get_androidversion_code()
        metadata['version_name'] = parsed_apk.get_androidversion_name()

        with ZipFile(apk_copy.name) as apk_zip:
            if extract_architecture_metadata:
                metadata['architecture'] = _extract_architecture(apk_zip, original_apk_path)

            if extract_locale_metadata:
                metadata['locales'] = _extract_locales(apk_zip)

            if extract_firefox_metadata:
                metadata['firefox_version'] = _extract_firefox_version(apk_zip)
                metadata['firefox_build_id'] = _extract_firefox_build_id(apk_zip)

    return metadata


def _extract_architecture(apk_zip, original_apk_path):
    files_with_architecture_in_path = [
        name for name in apk_zip.namelist()
        if name.startswith(_DIRECTORY_WITH_ARCHITECTURE_METADATA)
    ]

    if not files_with_architecture_in_path:
        raise BadApk('"{}" does not contain a directory called "{}"'
                     .format(original_apk_path, _DIRECTORY_WITH_ARCHITECTURE_METADATA))

    return _extract_architecture_from_paths(original_apk_path, files_with_architecture_in_path)


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
        raise BadApk('"{}" contains too many architectures: {}'.format(apk_path, unique_architectures))

    return unique_architectures[0]


def _extract_firefox_version(apk_zip):
    return _extract_value_from_application_ini(apk_zip, 'App.Version')


def _extract_firefox_build_id(apk_zip):
    return _extract_value_from_application_ini(apk_zip, 'App.BuildID')


def _extract_value_from_application_ini(apk_zip, full_key):
    config = ConfigParser()

    config.read_file(codecs.getreader('utf-8')(apk_zip.open('application.ini')))
    section, key = full_key.split('.')
    return config.get(section, key)


def _extract_locales(apk_zip):
    omni_ja_data = BytesIO(apk_zip.read(_OMNI_JA_LOCATION))
    with ZipFile(omni_ja_data) as omni_ja:
        with omni_ja.open(_CHROME_MANIFEST_LOCATION) as manifest:
            manifest_raw_lines = manifest.readlines()

    locales = _get_unique_locales(manifest_raw_lines)

    if len(locales) == 0:
        raise NoLocaleFound(apk_zip, _OMNI_JA_LOCATION, _CHROME_MANIFEST_LOCATION)

    return locales


def _get_unique_locales(manifest_raw_lines):
    manifest_lines = [line.decode('utf-8') for line in manifest_raw_lines]

    locales = [
        _LOCALE_LINE_PATTERN.match(line).group(1) for line in manifest_lines
        if _LOCALE_LINE_PATTERN.match(line) is not None
    ]

    return tuple(sorted(filter_out_identical_values(locales)))
