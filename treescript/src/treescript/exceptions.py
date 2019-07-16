"""Treescript exceptions."""
from scriptworker_client.exceptions import TaskError, TaskVerificationError


class TaskVerificationError(TaskVerificationError):
    """Something went wrong during task verification."""


class TreeScriptError(TaskError):
    """Something went wrong with treescript."""


class FailedSubprocess(TreeScriptError):
    """Something went wrong during a subprocess exec."""


class CheckoutError(TreeScriptError):
    """Something went wrong during a checkout."""


class PushError(TreeScriptError):
    """Something went wrong during a push."""
