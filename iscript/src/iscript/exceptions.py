"""iScript exceptions."""
from scriptworker_client.exceptions import TaskError


class IScriptError(TaskError):
    """Something went wrong with signing script."""


class FailedSubprocess(IScriptError):
    """Something went wrong during a subprocess exec."""


class UnknownAppDir(IScriptError):
    """There is no single app dir found for an app."""


class InvalidNotarization(IScriptError):
    """Apple returned an invalid status during notarization polling."""


class ThrottledNotarization(IScriptError):
    """Apple returned an error telling us we hit our upload limit."""


class UnknownNotarizationError(IScriptError):
    """Apple returned an unknown error response during notarization submission."""


class TimeoutError(IScriptError):
    """We have hit a timeout."""
