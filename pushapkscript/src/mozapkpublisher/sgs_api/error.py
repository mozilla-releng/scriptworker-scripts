from mozapkpublisher.common.exceptions import StoreException


class SgsException(StoreException):
    pass


class SgsAuthenticationException(SgsException):
    pass


class SgsAuthorizationException(SgsException):
    pass


class SgsUploadException(SgsException):
    pass


class SgsContentInfoException(SgsException):
    pass


class SgsUpdateException(SgsException):
    pass
