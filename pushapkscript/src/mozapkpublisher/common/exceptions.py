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


class NoTransactionError(LoggedError):
    def __init__(self, package_name):
        super(NoTransactionError, self).__init__(
            'Transaction has not been started for package "{}"'.format(package_name)
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


class NoTranslationGiven(LoggedError):
    def __init__(self, given_translations):
        super(NoTranslationGiven, self).__init__(
            msg='"{}" doesn\'t contain any item to work with'.format(given_translations)
        )


class TranslationMissingData(LoggedError):
    def __init__(self, locale_name, additional_message):
        super(TranslationMissingData, self).__init__(
            msg='Locale "{}" misses some data: {}'.format(locale_name, additional_message)
        )
