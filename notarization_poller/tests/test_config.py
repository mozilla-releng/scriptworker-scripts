#!/usr/bin/env python
# coding=utf-8
"""Test notarization_poller.config
"""
import json
import logging
import os
from copy import deepcopy

import pytest
from frozendict import frozendict

import notarization_poller.config as npconfig
from notarization_poller.constants import DEFAULT_CONFIG
from notarization_poller.exceptions import ConfigError


# constants helpers and fixtures {{{1
def close_handlers(log_name=None):
    log_name = log_name or __name__.split(".")[0]
    log = logging.getLogger(log_name)
    handlers = log.handlers[:]
    for handler in handlers:
        handler.close()
        log.removeHandler(handler)
    log.addHandler(logging.NullHandler())


# update_logging_config {{{1
def test_update_logging_config_verbose(config):
    config["verbose"] = True
    npconfig.update_logging_config(config, log_name=config["log_dir"])
    log = logging.getLogger(config["log_dir"])
    assert log.level == logging.DEBUG
    assert len(log.handlers) == 3
    close_handlers(log_name=config["log_dir"])


def test_update_logging_config_verbose_existing_handler(config):
    log = logging.getLogger(config["log_dir"])
    log.addHandler(logging.NullHandler())
    log.addHandler(logging.NullHandler())
    config["verbose"] = True
    npconfig.update_logging_config(config, log_name=config["log_dir"])
    assert log.level == logging.DEBUG
    assert len(log.handlers) == 4
    close_handlers(log_name=config["log_dir"])


def test_update_logging_config_not_verbose(config):
    config["verbose"] = False
    npconfig.update_logging_config(config, log_name=config["log_dir"])
    log = logging.getLogger(config["log_dir"])
    assert log.level == logging.INFO
    assert len(log.handlers) == 3
    close_handlers(log_name=config["log_dir"])


def test_watched_log_file(config):
    config["watch_log_file"] = True
    config["log_fmt"] = "%(levelname)s - %(message)s"
    npconfig.update_logging_config(config, log_name=config["log_dir"])
    path = os.path.join(config["log_dir"], "worker.log")
    log = logging.getLogger(config["log_dir"])
    log.info("foo")
    os.rename(path, "{}.1".format(path))
    log.info("bar")
    with open(path, "r") as fh:
        assert fh.read().rstrip() == "INFO - bar"
    close_handlers(log_name=config["log_dir"])


# get_config_from_cmdln {{{1
def test_get_config_from_cmdln():
    path = os.path.join(os.path.dirname(__file__), "data", "good.json")
    c = deepcopy(dict(DEFAULT_CONFIG))
    with open(path) as fh:
        c.update(json.load(fh))
    expected_config = frozendict(c)

    config = npconfig.get_config_from_cmdln([path])
    assert config == expected_config


@pytest.mark.parametrize(
    "path,raises",
    ((os.path.join(os.path.dirname(__file__), "data", "good.json"), None), (os.path.join(os.path.dirname(__file__), "data", "bad.json"), ConfigError)),
)
def test_validate_config(path, raises):
    if raises:
        with pytest.raises(raises):
            npconfig.get_config_from_cmdln([path])
    else:
        npconfig.get_config_from_cmdln([path])
