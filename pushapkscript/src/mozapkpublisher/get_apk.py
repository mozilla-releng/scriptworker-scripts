#!/usr/bin/env python3

import aiohttp
import asyncio
import sys
import os
import re
import signal
import shutil
import logging

from argparse import ArgumentParser
from mozapkpublisher.common.apk.history import (
    get_expected_api_levels,
    get_firefox_major_version_number,
)
from mozapkpublisher.common.exceptions import CheckSumMismatch
from mozapkpublisher.common.utils import (
    download_file,
    file_sha512sum,
    load_json_url,
)

logger = logging.getLogger(__name__)

FTP_BASE_URL = 'https://ftp.mozilla.org/pub/mobile'
ARCH_VALUES = ["arm", "x86"]
JSON_VERSION_URL = "https://product-details.mozilla.org/1.0/firefox_versions.json"


class GetAPK:
    # TODO: version and latest_nightly are mutually exclusive, improve abstraction so this class isn't if/else-ing
    def __init__(self, version, latest_nightly, build, arch, locale, download_directory):
        self.version = version
        self.latest_nightly = latest_nightly
        self.build = build
        self.arch = arch
        self.locale = locale
        self.download_directory = download_directory

    # Cleanup half downloaded files on Ctrl+C
    def signal_handler(self, signal, frame):
        print("You pressed Ctrl+C!")
        self.cleanup()
        sys.exit(1)

    def cleanup(self):
        try:
            shutil.rmtree(self.download_directory)
            logger.info('Download directory cleaned')
        except FileNotFoundError:
            logger.warning('{} was not found. Skipping...'.format(self.download_directory))

    async def download(self, session, version, build, architecture, locale):
        try:
            os.makedirs(self.download_directory)
        except FileExistsError:
            pass

        for api_suffix in get_api_suffix(version, architecture):
            apk_base_url = generate_apk_base_url(self.latest_nightly, version, build, locale, api_suffix)
            urls_and_locations = craft_apk_and_checksums_url_and_download_locations(
                apk_base_url, self.download_directory, version, build, locale, architecture,
                api_suffix, self.latest_nightly
            )
            apk = urls_and_locations['apk']
            checksums = urls_and_locations['checksums']

            await asyncio.gather(
                download_file(session, apk['url'], apk['download_location']),
                download_file(session, checksums['url'], checksums['download_location'])
            )

            check_apk_against_checksum_file(apk['download_location'], checksums['download_location'])

    def get_version_name(self):
        if self.latest_nightly:
            json = load_json_url(JSON_VERSION_URL)
            version_code = json['FIREFOX_NIGHTLY']
            return version_code
        return self.version

    # Download all the archs if none is given
    async def download_all(self, session, version, build, locale):
        download_coroutines = [
            self.download(session, version, build, architecture, locale)
            for architecture in ARCH_VALUES
        ]
        await asyncio.gather(*download_coroutines)

    async def run(self):
        # For latest-nightly, there's only one build, and the only locale is "en-US"
        # Perhaps instead of custom validation, this behaviour/validation should happen in our argparse validation.
        # The only downside to specifying this within argparse is that the best solution (IMHO) is
        # with subcommands (https://stackoverflow.com/a/17909525), but that's a breaking change
        if self.latest_nightly and (
                self.build != self.parser.get_default('build') or
                self.locale != self.parser.get_default('locale')):
            print('None of the arguments --build, --locale and --version can be used with --latest-nightly')
            sys.exit(1)

        version = self.get_version_name()
        architecture = self.arch
        build = str(self.build)
        locale = self.locale

        logger.info('Downloading version "{}" build #{} for arch "{}" (locale "{}")'.format(version, build, architecture, locale))

        async with aiohttp.ClientSession() as session:
            if architecture == "all":
                await self.download_all(session, version, build, locale)
            else:
                await self.download(session, version, build, architecture, locale)


def generate_apk_base_url(latest_nightly, version, build, locale, api_suffix):
    return '{}/nightly/latest-mozilla-central-android-{}'.format(FTP_BASE_URL, api_suffix) \
        if latest_nightly else \
        '{}/android-{}/{}'.format(
            generate_base_directory(version, build),
            api_suffix,
            locale,
        )


def get_api_suffix(version, arch):
    if arch != 'arm':
        return [arch]
    else:
        api_levels = get_expected_api_levels(version)
        # TODO support old schemes when no API level was in the path
        return [
            'api-{}'.format(api_level) for api_level in api_levels
        ]


def craft_apk_and_checksums_url_and_download_locations(base_apk_url, download_directory, version, build, locale,
                                                       architecture, api_suffix, latest_nightly):
    file_names = _craft_apk_and_checksums_file_names(version, locale, architecture)

    urls_and_locations = {
        extension: {
            'download_location': os.path.join(download_directory, file_name),
            'url': '/'.join([base_apk_url, file_name]),
        } for extension, file_name in file_names.items()
    }

    if latest_nightly:
        urls_and_locations['checksums']['url'] = \
            '{}/nightly/latest-mozilla-central-android-{}/en-US/fennec-{}.en-US.android-{}.checksums'.format(
                FTP_BASE_URL, api_suffix, version, _get_architecture_in_file_name(architecture)
            )
    elif get_firefox_major_version_number(version) >= 59:
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


def main():
    from mozapkpublisher.common import main_logging
    main_logging.init()

    parser = ArgumentParser(
        description='Download APKs of Firefox for Android (aka Fennec) from {}'.format(FTP_BASE_URL)
    )

    exclusive_group = parser.add_mutually_exclusive_group(required=True)
    exclusive_group.add_argument('--version', default=None, help='Specify version number to download (e.g. 23.0b7)')
    exclusive_group.add_argument('--latest-nightly', action='store_true', default=False,
                                 help='Download the latest nightly version')

    parser.add_argument('--build', type=int, default=1, help='Specify build number (default 1)')
    parser.add_argument(
        '--arch', choices=ARCH_VALUES, default='all',
        help='Specify which architecture to get the apk for. Will download every architecture if not set.'
    )
    parser.add_argument('--locale', default='multi', help='Specify which locale to get the apk for')
    parser.add_argument(
        '--output-directory', dest='download_directory', default='apk-download',
        help='Directory in which APKs will be downloaded to. Will be created if needed.'
    )

    config = parser.parse_args()
    myScript = GetAPK(config.version, config.latest_nightly, config.build, config.arch, config.locale, config.download_directory)
    signal.signal(signal.SIGINT, myScript.signal_handler)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(myScript.run())


__name__ == '__main__' and main()
