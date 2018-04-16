"""addonscript specific exceptions."""

from scriptworker.exceptions import ScriptWorkerRetryException


class SignatureError(ScriptWorkerRetryException):
    """Error when signed XPI is still missing or reported invalid by AMO."""

    pass


class FatalSignatureError(Exception):
    """Fatal error when signed XPI is still missing or reported invalid by AMO."""

    pass


class AMOConflictError(Exception):
    """Error when AMO returns 409-Conflict usually from a duplicate version."""

    def __init__(self, message):
        """Init and store the message to this exception."""
        self.message = message
        Exception.__init__(self, message)
