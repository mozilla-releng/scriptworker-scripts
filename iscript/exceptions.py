"""iScript exceptions."""
from scriptworker.exceptions import ScriptWorkerTaskException
from scriptworker.constants import STATUSES


class IScriptError(ScriptWorkerTaskException):
    """Something went wrong with signing script."""

    def __init__(self, msg):
        """Initialize IScriptError.

        Args:
            msg (str): the reason for throwing an exception.
        """
        super(IScriptError, self).__init__(
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
