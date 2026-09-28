from mozapkpublisher.common.exceptions import StoreException


class VivoException(StoreException):
    pass


class VivoAuthenticationException(VivoException):
    pass


class VivoAuthorizationException(VivoException):
    pass


class VivoUploadException(VivoException):
    pass


class VivoContentInfoException(VivoException):
    pass


class VivoUpdateException(VivoException):
    pass
