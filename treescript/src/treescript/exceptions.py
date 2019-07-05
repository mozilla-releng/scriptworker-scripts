"""Treescript exceptions."""
from scriptworker_client.exceptions import TaskError, TaskVerificationError


class TaskVerificationError(TaskVerificationError):
    """Something went wrong during task verification."""


class FailedSubprocess(TaskError):
    """Something went wrong during a subprocess exec."""


class TreeScriptError(TaskError):
    """Something went wrong with treescript."""
