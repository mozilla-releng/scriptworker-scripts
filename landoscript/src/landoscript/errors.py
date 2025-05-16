from scriptworker.client import STATUSES
from scriptworker.exceptions import ScriptWorkerTaskException


class LandoscriptError(ScriptWorkerTaskException):
    pass


class MergeConflictError(LandoscriptError):
    """Raised when a merge conflict error is returned by Lando. In most cases
    this is caused by racing with another landoscript job, and a retry will
    fix the problem (often by turning the task into a no-op)."""

    def __init__(self, *args):
        super().__init__(*args, exit_code=STATUSES["intermittent-task"])
