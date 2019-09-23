import logging

logger = logging.getLogger(__name__)


class LoggedError(Exception):
    def __init__(self, msg):
        logger.fatal(msg)
        super(LoggedError, self).__init__(msg)


class WrongArgumentGiven(LoggedError):
    pass


class CheckSumMismatch(LoggedError):
    def __init__(self, checked_file, expected, actual):
        super(CheckSumMismatch, self).__init__(
            msg='Downloading "{}" failed!. Checksum "{}" was expected, but actually got "{}"'
                .format(checked_file, expected, actual)
        )


class NotMultiLocaleApk(LoggedError):
    def __init__(self, apk_path, unique_locales):
        super(NotMultiLocaleApk, self).__init__(
            'Not a multilocale APK. "{}" contains only: {}'.format(apk_path, unique_locales)
        )


class NoLocaleFound(LoggedError):
    def __init__(self, apk_path, omni_ja_location, chrome_manifest_location):
        super(NoLocaleFound, self).__init__(
            'No locale detected in {}:{}:{}'.format(apk_path, omni_ja_location, chrome_manifest_location)
        )


class BadApk(LoggedError):
    pass


class BadSetOfApks(LoggedError):
    pass
