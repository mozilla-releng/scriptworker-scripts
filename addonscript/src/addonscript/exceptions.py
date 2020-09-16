"""addonscript specific exceptions."""

from scriptworker.constants import STATUSES
from scriptworker.exceptions import ScriptWorkerException, ScriptWorkerTaskException


class AuthFailedError(ScriptWorkerTaskException):
    """Fatal error when addonscript has misconfigured auth credentials."""

    pass


class AuthInsufficientPermissionsError(ScriptWorkerTaskException):
    """Fatal error when addonscript credentials don't have enough permissions"""

    pass


class SignatureError(ScriptWorkerException):
    """Error when signed XPI is still missing or reported invalid by AMO.

    Attributes:
        exit_code (int): this is set to 7 (intermittent-task).

    """

    exit_code = STATUSES["intermittent-task"]


class FatalSignatureError(ScriptWorkerTaskException):
    """Fatal error when signed XPI is still missing or reported invalid by AMO."""

    pass


class BadVersionError(ScriptWorkerTaskException):
    """Fatal error when XPI's version is invalid against AMO sanity checks."""

    pass


class AMOConflictError(Exception):
    """Error when AMO returns 409-Conflict usually from a duplicate version."""

    def __init__(self, message):
        """Init and store the message to this exception."""
        self.message = message
        Exception.__init__(self, message)
