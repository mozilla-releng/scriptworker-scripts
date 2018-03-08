"""Signingscript exceptions."""
from scriptworker.exceptions import ScriptWorkerTaskException
from scriptworker.constants import STATUSES


class SigningServerError(ScriptWorkerTaskException):
    """Something went wrong with the signing server."""

    def __init__(self, msg):
        """Initialize SigningServerError.

        Args:
            msg (str): the reason for throwing an exception.
        """
        super(SigningServerError, self).__init__(
            msg, exit_code=STATUSES['internal-error']
        )


class SigningScriptError(ScriptWorkerTaskException):
    """Something went wrong with signing script."""

    def __init__(self, msg):
        """Initialize SigningScriptError.

        Args:
            msg (str): the reason for throwing an exception.
        """
        super(SigningScriptError, self).__init__(
            msg, exit_code=STATUSES['internal-error']
        )


class FailedSubprocess(ScriptWorkerTaskException):
    """Something went wrong during a subprocess exec."""

    def __init__(self, msg):
        """Initialize FailedSubprocess.

        Args:
            msg (str): the reason for throwing an exception.
        """
        super(FailedSubprocess, self).__init__(
            msg, exit_code=STATUSES['internal-error']
        )
