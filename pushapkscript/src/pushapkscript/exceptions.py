from scriptworker.constants import STATUSES
from scriptworker.exceptions import ScriptWorkerTaskException


class SignatureError(ScriptWorkerTaskException):
    def __init__(self, msg):
        super().__init__(msg, exit_code=STATUSES["internal-error"])


class ConfigValidationError(ScriptWorkerTaskException):
    def __init__(self, msg):
        super().__init__(msg, exit_code=STATUSES["internal-error"])
