from scriptworker.exceptions import ScriptWorkerTaskException
from scriptworker.task import STATUSES


class TaskVerificationError(ScriptWorkerTaskException):
    def __init__(self, msg):
        super(TaskVerificationError, self).__init__(
            msg, exit_code=STATUSES['malformed-payload']
        )


class ChecksumMismatchError(ScriptWorkerTaskException):
    def __init__(self, msg):
        super(ChecksumMismatchError, self).__init__(
            msg, exit_code=STATUSES['malformed-payload']
        )


class SigningServerError(ScriptWorkerTaskException):
    def __init__(self, msg):
        super(SigningServerError, self).__init__(
            msg, exit_code=STATUSES['internal-error']
        )
