#!/usr/bin/env python3

import sys
import os
import re
import signal
import shutil
import logging

from mozapkpublisher.common.base import Base, ArgumentParser
from mozapkpublisher.common.exceptions import CheckSumMismatch
from mozapkpublisher.common.utils import load_json_url, download_file, file_sha512sum

logger = logging.getLogger(__name__)

FTP_BASE_URL = 'https://ftp.mozilla.org/pub/mobile'


class GetAPK(Base):
    arch_values = ["arm", "x86"]
    multi_api_archs = ["arm"]
    multi_apis = ['api-15']     # v11 has been dropped in fx 46 (bug 1155801) and v9 in fx 48 (bug 1220184)

    json_version_url = "https://product-details.mozilla.org/1.0/firefox_versions.json"

    @classmethod
    def _init_parser(cls):
        cls.parser = ArgumentParser(
            description='Download APKs of Firefox for Android (aka Fennec) from {}'.format(FTP_BASE_URL)
        )

        exclusive_group = cls.parser.add_mutually_exclusive_group(required=True)
        exclusive_group.add_argument('--version', default=None, help='Specify version number to download (e.g. 23.0b7)')
        exclusive_group.add_argument('--latest-nightly', action='store_true', default=False,
                                     help='Download the latest nightly version')

        cls.parser.add_argument('--build', type=int, default=1, help='Specify build number (default 1)')
        cls.parser.add_argument(
            '--arch', choices=cls.arch_values, default='all',
            help='Specify which architecture to get the apk for. Will download every architecture if not set.'
        )
        cls.parser.add_argument('--locale', default='multi', help='Specify which locale to get the apk for')
        cls.parser.add_argument(
            '--output-directory', dest='download_directory', default='apk-download',
            help='Directory in which APKs will be downloaded to. Will be created if needed.'
        )

    # Cleanup half downloaded files on Ctrl+C
    def signal_handler(self, signal, frame):
        print("You pressed Ctrl+C!")
        self.cleanup()
        sys.exit(1)

    def cleanup(self):
        try:
            shutil.rmtree(self.config.download_directory)
            logger.info('Download directory cleaned')
        except OSError:     # XXX: Used for compatibility with Python 2. Use FileNotFoundError otherwise
            logger.warn('{} was not found. Skipping...'.format(self.config.download_directory))

    def generate_apk_base_url(self, version, build, locale, api_suffix):
        return '{}/nightly/latest-mozilla-central-android-{}'.format(FTP_BASE_URL, api_suffix) \
            if self.config.latest_nightly else \
            '{}/candidates/{}-candidates/build{}/android-{}/{}'.format(
                FTP_BASE_URL, version, build, api_suffix, locale,
            )

    def get_api_suffix(self, arch):
        return self.multi_apis if arch in self.multi_api_archs else [arch]

    def download(self, version, build, architecture, locale):
        try:
            os.makedirs(self.config.download_directory)
        except OSError:     # XXX: Used for compatibility with Python 2. Use FileExistsError otherwise
            pass

        for api_suffix in self.get_api_suffix(architecture):
            apk_base_url = self.generate_apk_base_url(version, build, locale, api_suffix)
            apk, checksums = craft_apk_and_checksums_url_and_download_locations(
                apk_base_url, self.config.download_directory, version, locale, architecture
            )

            download_file(apk['url'], apk['download_location'])
            download_file(checksums['url'], checksums['download_location'])

            check_apk_against_checksum_file(apk['download_location'], checksums['download_location'])

    def get_version_name(self):
        if self.config.latest_nightly:
            json = load_json_url(self.json_version_url)
            version_code = json['FIREFOX_NIGHTLY']
            return version_code
        return self.config.version

    # Download all the archs if none is given
    def download_all(self, version, build, locale):
        for architecture in self.arch_values:
            self.download(version, build, architecture, locale)

    def run(self):
        version = self.get_version_name()
        architecture = self.config.arch
        build = str(self.config.build)
        locale = self.config.locale

        logger.info('Downloading version "{}" build #{} for arch "{}" (locale "{}")'.format(version, build, architecture, locale))
        if architecture == "all":
            self.download_all(version, build, locale)
        else:
            self.download(version, build, architecture, locale)


def craft_apk_and_checksums_url_and_download_locations(base_apk_url, download_directory, version, locale, architecture):
    file_names = _craft_apk_and_checksums_file_names(version, locale, architecture)

    return [
        {
            'download_location': os.path.join(download_directory, file_name),
            'url': '/'.join([base_apk_url, file_name]),
        } for file_name in file_names
    ]


def _craft_apk_and_checksums_file_names(version, locale, architecture):
    file_name_architecture = _get_architecture_in_file_name(architecture)
    extensions = ['apk', 'checksums']

    return [
        'fennec-{}.{}.android-{}.{}'.format(version, locale, file_name_architecture, extension)
        for extension in extensions
    ]


def _get_architecture_in_file_name(architecture):
    # the file name contains i386 instead of x86
    return 'i386' if architecture == 'x86' else architecture


def check_apk_against_checksum_file(apk_file, checksum_file):
    logger.debug('Checking checksum for "{}"...'.format(apk_file))

    checksum = _fetch_checksum_from_file(checksum_file, apk_file)
    apk_checksum = file_sha512sum(apk_file)

    if checksum == apk_checksum:
        logger.info('Checksum for "{}" succeeded!'.format(apk_file))
        os.remove(checksum_file)
    else:
        raise CheckSumMismatch(apk_file, expected=apk_checksum, actual=checksum)


def _fetch_checksum_from_file(checksum_file, apk_file):
    base_apk_filepath = _take_out_common_path(checksum_file, apk_file)
    with open(checksum_file, 'r') as fh:
        for line in fh:
            m = re.match(r"""^(?P<hash>.*) sha512 (?P<filesize>\d+) {}""".format(base_apk_filepath), line)
            if m:
                gd = m.groupdict()
                logger.info("Found hash {}".format(gd['hash']))
                return gd['hash']
    # old style pre-Fennec 53 checksums files
    with open(checksum_file, 'r') as f:
        checksum = f.read()
    checksum = re.sub("\s(.*)", "", checksum.splitlines()[0])
    logger.info("Found hash {}".format(checksum))
    return checksum


def _take_out_common_path(checksum_file, apk_file):
    return os.path.relpath(apk_file, os.path.dirname(checksum_file))


if __name__ == '__main__':
    from mozapkpublisher.common import main_logging
    main_logging.init()

    myScript = GetAPK()
    signal.signal(signal.SIGINT, myScript.signal_handler)
    myScript.run()
