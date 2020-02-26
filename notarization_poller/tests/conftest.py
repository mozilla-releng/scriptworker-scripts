#!/usr/bin/env python
# coding=utf-8
"""Test notarization_poller.config
"""
import json
import os
from copy import deepcopy

import pytest

from notarization_poller.constants import DEFAULT_CONFIG
from scriptworker_client.utils import makedirs


@pytest.fixture(scope="function")
def config(tmpdir):
    _config = deepcopy(dict(DEFAULT_CONFIG))
    with open(os.path.join(os.path.dirname(__file__), "data", "good.json")) as fh:
        _config.update(json.load(fh))
    _config["artifact_dir"] = os.path.join(str(tmpdir), "artifacts")
    _config["log_dir"] = os.path.join(str(tmpdir), "logs")
    _config["work_dir"] = os.path.join(str(tmpdir), "work")
    for name in ("artifact_dir", "log_dir", "work_dir"):
        makedirs(_config[name])
    yield _config
