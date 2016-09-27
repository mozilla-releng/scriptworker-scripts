#!/usr/bin/env python

import sys
import os
import re
import signal
import argparse
import shutil
import logging

from mozapkpublisher.base import Base
from mozapkpublisher.utils import load_json_url, download_file, file_sha512sum
from mozapkpublisher.exceptions import CheckSumMismatch

logger = logging.getLogger(__name__)


class GetAPK(Base):
    arch_values = ["arm", "x86"]
    multi_api_archs = ["arm"]
    multi_apis = ['api-15']     # v11 has been dropped in fx 46 (bug 1155801) and v9 in fx 48 (bug 1220184)

    download_dir = "apk-download"

    apk_ext = ".apk"
    checksums_ext = ".checksums"
    android_prefix = "android-"

    base_url = "https://ftp.mozilla.org/pub/mobile"
    json_version_url = "https://product-details.mozilla.org/1.0/firefox_versions.json"

    def __init__(self, config=None):
        self.config = self._parse_config(config)

    @classmethod
    def _init_parser(cls):
        cls.parser = argparse.ArgumentParser(
            description='Download the apk of Firefox for Android from {}'.format(cls.base_url)
        )

        exclusive_group = cls.parser.add_mutually_exclusive_group(required=True)
        exclusive_group.add_argument('--clean', action='store_true', default=False,
                                     help='Use this option to clean the download directory')
        exclusive_group.add_argument('--version', default=None, help='Specify version number to download (e.g. 23.0b7)')
        exclusive_group.add_argument('--latest-nightly', action='store_true', default=False,
                                     help='Download the latest nightly version')
        exclusive_group.add_argument('--latest-aurora', action='store_true', default=False,
                                     help='Download the latest aurora version')

        cls.parser.add_argument('--build', type=int, default=1, help='Specify build number (default 1)')
        cls.parser.add_argument(
            '--arch', choices=cls.arch_values, default='all',
            help='Specify which architecture to get the apk for. Will download every architecture if not set.'
        )
        cls.parser.add_argument('--locale', default='multi', help='Specify which locale to get the apk for')

    # Cleanup half downloaded files on Ctrl+C
    def signal_handler(self, signal, frame):
        print("You pressed Ctrl+C!")
        self.cleanup()
        sys.exit(1)

    def cleanup(self):
        try:
            shutil.rmtree(self.download_dir)
            logger.info('Download directory cleaned')
        except OSError:     # XXX: Used for compatibility with Python. Use FileNotFoundError otherwise
            logger.warn('{} was not found. Skipping...'.format(self.download_dir))

    # Gets called once download is complete
    def download_complete(self, apk_file, checksum_file):
        logger.info(apk_file + " has been downloaded successfully")
        os.remove(checksum_file)

    # Check the given values are correct
    def check_argument(self):
        if self.config.clean:
            self.cleanup()
        if self.config.version is None:
            if self.config.clean:
                sys.exit(0)

    # Checksum check the APK
    def check_apk(self, apk_file, checksum_file):
        logger.info("The checksum for the APK is being checked....")
        with open(checksum_file, 'r') as f:
            checksum = f.read()
        checksum = re.sub("\s(.*)", "", checksum.splitlines()[0])

        apk_checksum = file_sha512sum(apk_file)

        if checksum == apk_checksum:
            logger.info("APK checksum check succeeded!")
            self.download_complete(apk_file, checksum_file)
        else:
            shutil.rmtree(self.download_dir)
            raise CheckSumMismatch(apk_file, expected=apk_checksum, actual=checksum)

    # Helper functions
    def generate_url(self, version, build, locale, api_suffix, arch_file):
        if self.config.latest_nightly or self.config.latest_aurora:
            code = "central" if self.config.latest_nightly else "aurora"
            return ("%s/nightly/latest-mozilla-%s-android-%s/fennec-%s.%s.android-%s") % (
                self.base_url, code, api_suffix, version, locale, arch_file
            )

        return ("%s/candidates/%s-candidates/build%s/%s%s/%s/fennec-%s.%s.%s%s") % (
            self.base_url, version, build, self.android_prefix, api_suffix, locale, version, locale,
            self.android_prefix, arch_file
        )

    def get_api_suffix(self, arch):
        if arch in self.multi_api_archs:
            return self.multi_apis
        else:
            return [arch]

    def get_arch_file(self, arch):
        if arch == "x86":
            # the filename contains i386 instead of x86
            return "i386"
        else:
            return arch

    def get_common_file_name(self, version, locale):
        return "fennec-" + version + "." + locale + "." + self.android_prefix

    def download(self, version, build, arch, locale):
        try:
            os.makedirs(self.download_dir)
        except OSError:     # XXX: Used for compatibility with Python. Use FileExistsError otherwise
            pass

        common_filename = self.get_common_file_name(version, locale)
        arch_file = self.get_arch_file(arch)

        for api_suffix in self.get_api_suffix(arch):
            url = self.generate_url(version, build, locale, api_suffix, arch_file)
            apk_url = url + self.apk_ext
            checksum_url = url + self.checksums_ext
            if arch in self.multi_api_archs:
                filename = common_filename + arch_file + "-" + api_suffix
            else:
                filename = common_filename + arch_file

            filename_apk = os.path.join(self.download_dir, filename + self.apk_ext)
            filename_checksums = os.path.join(self.download_dir, filename + self.checksums_ext)

            download_file(self, apk_url, filename_apk)
            download_file(self, checksum_url, filename_checksums)

            self.check_apk(filename_apk, filename_checksums)

    def get_version_name(self):
        if self.config.latest_nightly or self.config.latest_aurora:
            json = load_json_url(self.json_version_url)
            version_code = json['FIREFOX_NIGHTLY'] if self.config.latest_nightly else json['FIREFOX_AURORA']
            return version_code
        return self.config.version

    # Download all the archs if none is given
    def download_all(self, version, build, locale):
        for arch in self.arch_values:
            self.download(version, build, arch, locale)

    # Download apk initial action
    def download_apk(self):
        self.check_argument()
        version = self.get_version_name()
        arch = self.config.arch
        build = str(self.config.build)
        locale = self.config.locale

        logger.info("Downloading version " + version + " build #" + build
                    + " for arch " + arch + " (locale " + locale + ")")
        if arch == "all":
            self.download_all(version, build, locale)
        else:
            self.download(version, build, arch, locale)

    def run(self):
        self.download_apk()


if __name__ == '__main__':
    from mozapkpublisher import main_logging
    main_logging.init()

    myScript = GetAPK()
    signal.signal(signal.SIGINT, myScript.signal_handler)
    myScript.run()
