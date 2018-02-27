import logging
import os

from unittest.mock import MagicMock
from pushsnapscript.script import craft_logging_config, get_default_config


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


def test_get_default_config(monkeypatch):
    monkeypatch.setattr(os, 'getcwd', lambda: '/a/current/dir')

    assert get_default_config() == {
        'work_dir': '/a/current/work_dir',
        'schema_file': '/a/current/dir/pushsnapscript/data/push_snap_task_schema.json',
        'verbose': False,
    }
