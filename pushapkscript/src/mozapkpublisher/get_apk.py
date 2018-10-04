#!/usr/bin/env python3

import sys
import os
import re
import signal
import shutil
import logging

from mozapkpublisher.common.apk.history import get_expected_api_levels_for_version, get_firefox_major_version_number
from mozapkpublisher.common.base import Base, ArgumentParser
from mozapkpublisher.common.exceptions import CheckSumMismatch
from mozapkpublisher.common.utils import load_json_url, download_file, file_sha512sum

logger = logging.getLogger(__name__)

FTP_BASE_URL = 'https://ftp.mozilla.org/pub/mobile'


class GetAPK(Base):
    arch_values = ["arm", "x86"]

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
        except FileNotFoundError:
            logger.warning('{} was not found. Skipping...'.format(self.config.download_directory))

    def generate_apk_base_url(self, version, build, locale, api_suffix):
        return '{}/nightly/latest-mozilla-central-android-{}'.format(FTP_BASE_URL, api_suffix) \
            if self.config.latest_nightly else \
            '{}/android-{}/{}'.format(
                generate_base_directory(version, build),
                api_suffix,
                locale,
            )

    def get_api_suffix(self, version, arch):
        if arch != 'arm':
            return [arch]
        else:
            api_levels = get_expected_api_levels_for_version(version)
            # TODO support old schemes when no API level was in the path
            return [
                'api-{}'.format(api_level) for api_level in api_levels
            ]

    def download(self, version, build, architecture, locale):
        try:
            os.makedirs(self.config.download_directory)
        except FileExistsError:
            pass

        for api_suffix in self.get_api_suffix(version, architecture):
            apk_base_url = self.generate_apk_base_url(version, build, locale, api_suffix)
            urls_and_locations = craft_apk_and_checksums_url_and_download_locations(
                apk_base_url, self.config.download_directory, version, build, locale, architecture
            )
            apk = urls_and_locations['apk']
            checksums = urls_and_locations['checksums']

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


def craft_apk_and_checksums_url_and_download_locations(base_apk_url, download_directory, version, build, locale, architecture):
    file_names = _craft_apk_and_checksums_file_names(version, locale, architecture)

    urls_and_locations = {
        extension: {
            'download_location': os.path.join(download_directory, file_name),
            'url': '/'.join([base_apk_url, file_name]),
        } for extension, file_name in file_names.items()
    }

    if get_firefox_major_version_number(version) >= 59:
        urls_and_locations['checksums']['url'] = '{}/{}'.format(
            generate_base_directory(version, build), 'SHA512SUMS'
        )

    return urls_and_locations


def generate_base_directory(version, build):
    return '{}/candidates/{}-candidates/build{}'.format(FTP_BASE_URL, version, build)


def _craft_apk_and_checksums_file_names(version, locale, architecture):
    file_name_architecture = _get_architecture_in_file_name(architecture)
    extensions = ['apk', 'checksums']

    return {
        extension: 'fennec-{}.{}.android-{}.{}'.format(version, locale, file_name_architecture, extension)
        for extension in extensions
    }


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

    # pre-Fennec 58 style
    checksum = _match_checksum_regex(
        checksum_file,  r"""^(?P<hash>.*) sha512 (?P<filesize>\d+) {}""".format(base_apk_filepath)
    )

    if not checksum:
        # post-Fennec 58. More greedy
        checksum = _match_checksum_regex(
            checksum_file,  r"""^(?P<hash>.*)  {}""".format(base_apk_filepath)
        )

        if not checksum:
            # old style pre-Fennec 53 checksums files. Super greedy
            with open(checksum_file, 'r') as f:
                checksum = f.read()
            checksum = re.sub(r'\s(.*)', '', checksum.splitlines()[0])

    logger.info("Found hash {}".format(checksum))
    return checksum


def _match_checksum_regex(checksum_file, regex):
    with open(checksum_file, 'r') as fh:
        for line in fh:
            m = re.match(regex, line)
            if m:
                gd = m.groupdict()
                return gd['hash']
    return None


def _take_out_common_path(checksum_file, apk_file):
    return os.path.relpath(apk_file, os.path.dirname(checksum_file))


if __name__ == '__main__':
    from mozapkpublisher.common import main_logging
    main_logging.init()

    myScript = GetAPK()
    signal.signal(signal.SIGINT, myScript.signal_handler)
    myScript.run()
