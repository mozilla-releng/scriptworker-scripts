#!/usr/bin/env python
"""Config for scriptworker.

Attributes:
    DEFAULT_CONFIG (frozendict): the default configuration
    log (logging.Logger): the log object for the module.

"""
import argparse
import logging
import logging.handlers
import os

from notarization_poller.constants import DEFAULT_CONFIG
from notarization_poller.exceptions import ConfigError
from scriptworker_client.client import init_config

log = logging.getLogger(__name__)


def update_logging_config(config, log_name=None, file_name="worker.log"):
    """Update python logging settings from config.

    By default, this sets the ``scriptworker`` log settings, but this will
    change if some other package calls this function or specifies the ``log_name``.

    * Use formatting from config settings.
    * Log to screen if ``verbose``
    * Add a rotating logfile from config settings.

    Args:
        config (dict): the running config
        log_name (str, optional): the name of the Logger to modify.
            If None, use the top level module ('scriptworker').
            Defaults to None.

    """
    log_name = log_name or __name__.split(".")[0]
    top_level_logger = logging.getLogger(log_name)

    datefmt = config["log_datefmt"]
    fmt = config["log_fmt"]
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    if config.get("verbose"):
        top_level_logger.setLevel(logging.DEBUG)
        if len(top_level_logger.handlers) == 0:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            top_level_logger.addHandler(handler)
    else:
        top_level_logger.setLevel(logging.INFO)

    # Rotating log file
    os.makedirs(config["log_dir"], exist_ok=True)
    path = os.path.join(config["log_dir"], file_name)
    if config["watch_log_file"]:
        # If we rotate the log file via logrotate.d, let's watch the file
        # so we can automatically close/reopen on move.
        handler = logging.handlers.WatchedFileHandler(path)
    else:
        # Avoid using WatchedFileHandler during scriptworker unittests
        handler = logging.FileHandler(path)
    handler.setFormatter(formatter)
    top_level_logger.addHandler(handler)
    top_level_logger.addHandler(logging.NullHandler())


# get_config_from_cmdln {{{1
def _validate_config(config):
    if "..." in config.values():
        raise ConfigError("Uninitialized value in config!")


def get_config_from_cmdln(args, desc="Run notarization poller"):
    """Load config from the args.

    Args:
        args (list): the commandline args. Generally ``sys.argv[1:]``

    Returns:
        frozendict: the config

    """
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("config_path", type=str, nargs="?", default="scriptworker.yaml", help="the path to the config file")
    parsed_args = parser.parse_args(args)
    config = init_config(config_path=parsed_args.config_path, default_config=DEFAULT_CONFIG, validator_callback=_validate_config)
    update_logging_config(config)
    return config
