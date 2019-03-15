#!/usr/bin/env python
# coding=utf-8
"""Test scriptworker_client.utils
"""
import aiohttp
import asyncio
from async_generator import asynccontextmanager
from datetime import datetime
import mock
import os
import pytest
import re
import shutil
import tempfile
import time
import scriptworker_client.utils as utils
from scriptworker_client.exceptions import RetryError, TaskError, TimeoutError


# load_json_or_yaml {{{1
@pytest.mark.parametrize("string,is_path,exception,raises,result", ((
    os.path.join(os.path.dirname(__file__), 'data', 'bad.json'),
    True, None, False, {"credentials": ["blah"]}
), (
    '{"a": "b"}', False, None, False, {"a": "b"}
), (
    '{"a": "b}', False, None, False, None
), (
    '{"a": "b}', False, TaskError, True, None
)))
def test_load_json_or_yaml(string, is_path, exception, raises, result):
    """
    """
    if raises:
        with pytest.raises(exception):
            utils.load_json_or_yaml(string, is_path=is_path, exception=exception)
    else:
        for file_type in ("json", "yaml"):
            assert result == utils.load_json_or_yaml(
                string, is_path=is_path, exception=exception, file_type=file_type
            )


#
