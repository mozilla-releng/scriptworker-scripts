# -*- coding: utf-8 -*-
import pytest

from balrogscript.test import config, nightly_config
from balrogscript.task import (get_task, get_task_channel, get_task_server,
                               get_upstream_artifacts)

assert nightly_config  # silence pyflakes
assert config  # silence pyflakes


def test_get_task_channel(nightly_config):
    task = get_task(nightly_config)
    with pytest.raises(NotImplementedError):
        get_task_channel(task, nightly_config)


@pytest.mark.parametrize("scopes,expected,raises", ((
    ["project:releng:balrog:server:dep", "project:releng:balrog:server:release"],
    None, True,
), (
    ["project:releng:balrog:server:!!"],
    None, True
), (
    ["project:releng:balrog:server:foo", "project:releng:balrog:action:foo"],
    None, True
), (
    ["project:releng:balrog:server:dep", "project:releng:balrog:action:foo"],
    "dep", False
)))
def test_get_task_server(nightly_config, scopes, expected, raises):
    task = get_task(nightly_config)
    task['scopes'] = scopes

    if raises:
        with pytest.raises(ValueError):
            get_task_server(task, nightly_config)
    else:
        assert expected == get_task_server(task, nightly_config)


@pytest.mark.parametrize("expected", ([
    [{
        u'paths': [u'public/manifest.json'],
        u'taskId': u'upstream-task-id',
        u'taskType': u'baz'
    }]
]))
def test_get_upstream_artifacts(nightly_config, expected):
    task = get_task(nightly_config)
    assert get_upstream_artifacts(task) == expected
