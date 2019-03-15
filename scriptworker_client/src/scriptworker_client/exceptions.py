#!/usr/bin/env python
"""Scriptworker-client exceptions."""

from scriptworker_client.constants import STATUSES


class ClientError(Exception):
    """Scriptworker-client base task error.

    To use::

        import sys
        try:
            ...
        except TaskError as exc:
            log.exception("log message")
            sys.exit(exc.exit_code)

    Attributes:
        exit_code (int): this is 1 by default (failure)

    """

    def __init__(self, *args, exit_code=1, **kwargs):
        """Initialize ClientError.

        Args:
            *args: These are passed on via super().
            exit_code (int, optional): The exit_code we should exit with when
                this exception is raised.  Defaults to 1 (failure).
            **kwargs: These are passed on via super().

        """
        self.exit_code = exit_code
        super(ClientError, self).__init__(*args, **kwargs)


class TaskError(ClientError):
    """Scriptworker-client base task error."""


class TimeoutError(ClientError):
    """Scriptworker-client timeout error."""


class TaskVerificationError(ClientError):
    """Verification error on a Taskcluster task.

    Use it when your script fails to verify any input from the task definition

    """

    def __init__(self, msg):
        """Initialize TaskVerificationError.

        Args:
            msg (string): the error message

        """
        super().__init__(msg, exit_code=STATUSES['malformed-payload'])


class RetryError(ClientError):
    """Scriptworker-client retry error."""
