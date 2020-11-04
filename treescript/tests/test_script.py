import json
import os
from unittest.mock import MagicMock

import mock
import pytest
from scriptworker_client.exceptions import TaskError

import treescript.script as script
from treescript.exceptions import TreeScriptError

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
@pytest.mark.parametrize("robustcheckout_works,raises,actions", ((False, TaskError, ["some_action"]), (True, None, ["some_action"]), (True, None, None)))
async def test_async_main(tmpdir, mocker, robustcheckout_works, raises, actions):
    async def fake_validate_robustcheckout(_):
        return robustcheckout_works

    def action_fun(*args, **kwargs):
        return actions

    mocker.patch.object(script, "task_action_types", new=action_fun)
    mocker.patch.object(script, "validate_robustcheckout_works", new=fake_validate_robustcheckout)
    mocker.patch.object(script, "log_mercurial_version", new=noop_async)
    mocker.patch.object(script, "do_actions", new=noop_async)
    config = mock.MagicMock()
    task = mock.MagicMock()
    if raises:
        with pytest.raises(raises):
            await script.async_main(config, task)
    else:
        await script.async_main(config, task)


# get_default_config {{{1
def test_get_default_config():
    parent_dir = os.path.dirname(os.getcwd())
    c = script.get_default_config()
    assert c["work_dir"] == os.path.join(parent_dir, "work_dir")


# do_actions {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "push_scope,push_payload,dry_run,push_expect_called",
    (
        (["push"], False, False, False),
        (["push"], False, True, False),
        (["push"], True, False, True),
        (["push"], True, True, False),
        ([], False, False, False),
        ([], False, True, False),
        ([], True, False, True),
        ([], True, True, False),
    ),
)
async def test_do_actions(mocker, push_scope, push_payload, dry_run, push_expect_called):
    actions = ["tag", "version_bump", "l10n_bump"]
    actions += push_scope
    called = {"version_bump": False, "l10n_bump": False, "merge": False}

    async def mocked_bump(*args, **kwargs):
        called["version_bump"] = True
        return 1

    async def mocked_l10n(*args, **kwargs):
        called["l10n_bump"] = True
        return 1

    async def mocked_perform_merge_actions(*args, **kwargs):
        called["merge"] = True

    vcs_mock = AsyncMock()
    vcs_mock.do_tagging.return_value = 1
    vcs_mock.log_outgoing.return_value = 3

    mocker.patch.object(script, "get_vcs_module", return_value=vcs_mock)
    mocker.patch.object(script, "bump_version", new=mocked_bump)
    mocker.patch.object(script, "l10n_bump", new=mocked_l10n)
    mocker.patch.object(script, "perform_merge_actions", new=mocked_perform_merge_actions)

    task_defn = {
        "payload": {"push": push_payload, "dry_run": dry_run},
        "metadata": {"source": "https://hg.mozilla.org/releases/mozilla-test-source" "/file/1b4ab9a276ce7bb217c02b83057586e7946860f9/taskcluster/ci/foobar"},
    }
    await script.do_actions({}, task_defn, actions, "/some/folder/here")

    assert called["merge"] is False
    vcs_mock.checkout_repo.assert_called_once()
    vcs_mock.do_tagging.assert_called_once()
    vcs_mock.log_outgoing.assert_called_once()
    vcs_mock.strip_outgoing.assert_called_once()
    if push_expect_called:
        vcs_mock.push.assert_called_once()
    else:
        vcs_mock.push.assert_not_called()


# do_actions {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "push_scope,push_payload,dry_run",
    (
        (["push"], False, False),
        (["push"], False, True),
        (["push"], True, False),
        (["push"], True, True),
        ([], False, False),
        ([], False, True),
        ([], True, False),
        ([], True, True),
    ),
)
async def test_do_actions_merge_tasks(mocker, push_scope, push_payload, dry_run):
    actions = ["merge_day"]
    actions += push_scope
    called = {"version_bump": False, "l10n_bump": False, "merge": False}

    async def mocked_bump(*args, **kwargs):
        called["version_bump"] = True
        return 1

    async def mocked_l10n(*args, **kwargs):
        called["l10n_bump"] = True
        return 1

    async def mocked_perform_merge_actions(*args, **kwargs):
        called["merge"] = True

    vcs_mock = AsyncMock()
    vcs_mock.do_tagging.return_value = 1
    vcs_mock.log_outgoing.return_value = 0

    mocker.patch.object(script, "get_vcs_module", return_value=vcs_mock)
    mocker.patch.object(script, "bump_version", new=mocked_bump)
    mocker.patch.object(script, "l10n_bump", new=mocked_l10n)
    mocker.patch.object(script, "perform_merge_actions", new=mocked_perform_merge_actions)

    task_defn = {
        "payload": {"push": push_payload, "dry_run": dry_run},
        "metadata": {"source": "https://hg.mozilla.org/releases/mozilla-test-source" "/file/1b4ab9a276ce7bb217c02b83057586e7946860f9/taskcluster/ci/foobar"},
    }
    await script.do_actions({}, task_defn, actions, "/some/folder/here")
    for action in ["version_bump", "l10n_bump"]:
        assert called[action] is False
    assert called["merge"] is True

    vcs_mock.checkout_repo.assert_called_once()
    vcs_mock.log_outgoing.assert_not_called()
    vcs_mock.strip_outgoing.assert_not_called()


# do_actions {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "push_scope,should_push,push_expect_called", ((["push"], False, False), (["push"], True, True), ([], False, False), ([], False, False))
)
async def test_perform_merge_actions(mocker, push_scope, should_push, push_expect_called):
    actions = ["merge_day"]
    actions += push_scope
    called = {"merge": False}

    async def mocked_do_merge(*args, **kwargs):
        called["merge"] = True
        return [("https://hg.mozilla.org/treescript-test", ".")]

    vcs_mock = AsyncMock()

    mocker.patch.object(script, "get_vcs_module", return_value=vcs_mock)
    mocker.patch.object(script, "do_merge", new=mocked_do_merge)
    mocker.patch.object(script, "should_push", return_value=should_push)
    await script.perform_merge_actions({}, {}, actions, "/some/folder/here", "hg")
    assert called["merge"] is True
    if push_expect_called:
        vcs_mock.push.assert_called_once()
    else:
        vcs_mock.push.assert_not_called()


@pytest.mark.asyncio
async def test_do_actions_no_changes(mocker):
    actions = ["push"]
    called = {"bump": False, "l10n": False}

    async def mocked_bump(*args, **kwargs):
        called["bump"] = True
        return 1

    async def mocked_l10n(*args, **kwargs):
        called["l10n"] = True
        return 1

    vcs_mock = AsyncMock()
    vcs_mock.log_outgoing.return_value = 0

    mocker.patch.object(script, "get_vcs_module", return_value=vcs_mock)
    mocker.patch.object(script, "bump_version", new=mocked_bump)
    mocker.patch.object(script, "l10n_bump", new=mocked_l10n)
    await script.do_actions({}, {"metadata": {"source": "https://hg.mozilla.org/file/"}, "payload": {"push": True}}, actions, "/some/folder/here")
    assert not any(called.values())
    vcs_mock.checkout_repo.assert_called_once()
    vcs_mock.do_tagging.assert_not_called()
    vcs_mock.log_outgoing.assert_called_once()
    vcs_mock.strip_outgoing.assert_called_once()
    vcs_mock.push.assert_not_called()


@pytest.mark.asyncio
async def test_do_actions_mismatch_change_count(mocker):
    actions = ["tag"]

    async def mocked_bump(*args, **kwargs):
        return 1

    async def mocked_l10n(*args, **kwargs):
        return 1

    vcs_mock = AsyncMock()
    vcs_mock.log_outgoing.return_value = 14

    mocker.patch.object(script, "get_vcs_module", return_value=vcs_mock)
    mocker.patch.object(script, "bump_version", new=mocked_bump)
    mocker.patch.object(script, "l10n_bump", new=mocked_l10n)
    with pytest.raises(TreeScriptError):
        await script.do_actions({}, {"metadata": {"source": "https://hg.mozilla.org/file/"}, "payload": {"push": False}}, actions, "/some/folder/here")


def test_main(monkeypatch):
    sync_main_mock = MagicMock()
    monkeypatch.setattr(script, "sync_main", sync_main_mock)
    script.main()
    sync_main_mock.asset_called_once_with(script.async_main, default_config=script.get_default_config())
