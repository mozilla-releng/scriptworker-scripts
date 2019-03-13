#!/usr/bin/env python
"""Scriptworker-client exceptions."""

from scriptworker_client.constants import STATUSES


class ClientError(Exception):
    """The base exception in scriptworker-client.

    When raised inside of the run_loop loop, set the taskcluster task
    status to at least ``self.exit_code``.

    Attributes:
        exit_code (int): this is set to 5 (internal-error).

    """

    exit_code = STATUSES['internal-error']


class BaseTaskError(ClientError):
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
        """Initialize TaskError.

        Args:
            *args: These are passed on via super().
            exit_code (int, optional): The exit_code we should exit with when
                this exception is raised.  Defaults to 1 (failure).
            **kwargs: These are passed on via super().

        """
        self.exit_code = exit_code
        super(TaskError, self).__init__(*args, **kwargs)


class TaskError(BaseTaskError):
    """Scriptworker-client task error"""
    pass


class TimeoutError(BaseTaskError):
    """Scriptworker-client timeout error"""


class TaskVerificationError(BaseTaskError):
    """Verification error on a Taskcluster task.

    Use it when your script fails to validate any input from the task definition

    """

    def __init__(self, msg):
        """Initialize TaskVerificationError.

        Args:
            msg (string): the error message

        """
        super().__init__(msg, exit_code=STATUSES['malformed-payload'])


class RetryError(BaseTaskError):
    """Scriptworker-client retry error"""
