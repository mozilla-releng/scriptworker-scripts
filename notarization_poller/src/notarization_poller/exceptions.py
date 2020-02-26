#!/usr/bin/env python
"""Notarization poller exceptions."""

from scriptworker_client.constants import STATUSES


class WorkerError(Exception):
    """The base exception in notarization poller.

    When raised inside of the run_loop loop, set the taskcluster task
    status to at least ``self.exit_code``.

    Attributes:
        exit_code (int): this is set to 5 (internal-error).

    """

    exit_code = STATUSES["internal-error"]


class RetryError(WorkerError):
    """worker retry error.

    Attributes:
        exit_code (int): this is set to 4 (resource-unavailable)

    """

    exit_code = STATUSES["resource-unavailable"]


class ConfigError(WorkerError):
    """Invalid configuration provided to the worker.

    Attributes:
        exit_code (int): this is set to 5 (internal-error).

    """
