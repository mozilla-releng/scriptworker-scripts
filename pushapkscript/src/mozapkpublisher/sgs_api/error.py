class SgsException(Exception):
    def __init__(self, message: str):
        self.message = message


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
