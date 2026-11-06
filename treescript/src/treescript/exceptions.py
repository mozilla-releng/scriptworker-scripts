"""Treescript exceptions."""

import scriptworker_client.exceptions as sce


class TaskVerificationError(sce.TaskVerificationError):
    """Something went wrong during task verification."""


class TreeScriptError(sce.TaskError):
    """Something went wrong with treescript."""
