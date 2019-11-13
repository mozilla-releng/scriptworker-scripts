"""Treescript exceptions."""
import scriptworker_client.exceptions as sce


class TaskVerificationError(sce.TaskVerificationError):
    """Something went wrong during task verification."""


class TreeScriptError(sce.TaskError):
    """Something went wrong with treescript."""


class FailedSubprocess(TreeScriptError):
    """Something went wrong during a subprocess exec."""


class CheckoutError(TreeScriptError):
    """Something went wrong during a checkout."""


class PushError(TreeScriptError):
    """Something went wrong during a push."""
