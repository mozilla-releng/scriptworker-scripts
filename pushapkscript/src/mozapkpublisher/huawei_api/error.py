from mozapkpublisher.common.exceptions import StoreException


class HuaweiException(StoreException):
    pass


class HuaweiAuthenticationException(HuaweiException):
    pass


class HuaweiAuthorizationException(HuaweiException):
    pass


class HuaweiUploadException(HuaweiException):
    pass


class HuaweiContentInfoException(HuaweiException):
    pass


class HuaweiUpdateException(HuaweiException):
    pass
