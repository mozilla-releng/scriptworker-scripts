import logging

from unittest.mock import MagicMock
from bouncerscript.script import craft_logging_config


def test_craft_logging_config():
    context = MagicMock()
    context.config = {'verbose': True}

    assert craft_logging_config(context) == {
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'level': logging.DEBUG
    }

    context.config = {'verbose': False}
    assert craft_logging_config(context) == {
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'level': logging.INFO
    }
