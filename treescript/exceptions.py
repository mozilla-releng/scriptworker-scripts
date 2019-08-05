"""Treescript exceptions."""
from scriptworker.exceptions import ScriptWorkerTaskException
from scriptworker.constants import STATUSES


class TaskVerificationError(ScriptWorkerTaskException):
    """Something went wrong during task verification."""

    def __init__(self, msg):
        """Initialize TaskVerificationError.

        Args:
            msg (str): the reason for throwing an exception.

        """
        super(TaskVerificationError, self).__init__(
            msg, exit_code=STATUSES['malformed-payload']
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
