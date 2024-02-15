import inspect
import json
import os
from unittest.mock import MagicMock

import mock
import pytest
from scriptworker_client.exceptions import TaskError

from treescript import gecko, github, script
from treescript.exceptions import TaskVerificationError, TreeScriptError

try:
    from unittest.mock import AsyncMock
except ImportError:
    # TODO: Remove this import once py3.7 is not supported anymore
    from mock import AsyncMock

# helper constants, fixtures, functions {{{1
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
EXAMPLE_CONFIG = os.path.join(BASE_DIR, "config_example.json")


def noop_sync(*args, **kwargs):
    pass


async def noop_async(*args, **kwargs):
    pass


def read_file(path):
    with open(path, "r") as fh:
        return fh.read()


def get_conf_file(tmpdir, **kwargs):
    conf = json.loads(read_file(EXAMPLE_CONFIG))
    conf.update(kwargs)
    conf["work_dir"] = os.path.join(tmpdir, "work")
    conf["artifact_dir"] = os.path.join(tmpdir, "artifact")
    path = os.path.join(tmpdir, "new_config.json")
    with open(path, "w") as fh:
        json.dump(conf, fh)
    return path


async def die_async(*args, **kwargs):
    raise TaskError("Expected exception.")


# async_main {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "task,expected",
    (
        ({"payload": {"source_repo": "https://github.com/foo/bar"}}, "github"),
        ({"payload": {"source_repo": "https://hg.mozilla.org/foo"}}, "gecko"),
        ({"payload": {}}, TaskVerificationError),
    ),
)
async def test_async_main(mocker, task, expected):
    gecko_mock = AsyncMock()
    github_mock = AsyncMock()
    mocker.patch.object(gecko, "do_actions", new=gecko_mock)
    mocker.patch.object(github, "do_actions", new=github_mock)
    config = mock.MagicMock()
    if inspect.isclass(expected) and issubclass(expected, Exception):
        with pytest.raises(expected):
            await script.async_main(config, task)
    else:
        await script.async_main(config, task)
        if expected == "github":
            assert github_mock.called_with(config, task)
            assert not gecko_mock.called
        elif expected == "gecko":
            assert gecko_mock.called_with(config, task)
            assert not github_mock.called


# get_default_config {{{1
def test_get_default_config():
    parent_dir = os.path.dirname(os.getcwd())
    c = script.get_default_config()
    assert c["work_dir"] == os.path.join(parent_dir, "work_dir")


def test_main(monkeypatch):
    sync_main_mock = MagicMock()
    monkeypatch.setattr(script, "sync_main", sync_main_mock)
    script.main()
    sync_main_mock.asset_called_once_with(script.async_main, default_config=script.get_default_config())
