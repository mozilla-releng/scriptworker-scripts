from unittest.mock import AsyncMock

import pytest

from treescript import gecko, script
from treescript.exceptions import TreeScriptError


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

    mocker.patch.object(gecko, "vcs", new=vcs_mock)
    mocker.patch.object(gecko, "bump_version", new=mocked_bump)
    mocker.patch.object(gecko, "l10n_bump", new=mocked_l10n)
    mocker.patch.object(gecko, "perform_merge_actions", new=mocked_perform_merge_actions)

    task_defn = {
        "payload": {"push": push_payload, "dry_run": dry_run, "actions": actions},
        "metadata": {"source": "https://hg.mozilla.org/releases/mozilla-test-source" "/file/1b4ab9a276ce7bb217c02b83057586e7946860f9/taskcluster/ci/foobar"},
    }
    await gecko.do_actions({"work_dir": "foo"}, task_defn)

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

    mocker.patch.object(gecko, "vcs", new=vcs_mock)
    mocker.patch.object(gecko, "bump_version", new=mocked_bump)
    mocker.patch.object(gecko, "l10n_bump", new=mocked_l10n)
    mocker.patch.object(gecko, "perform_merge_actions", new=mocked_perform_merge_actions)

    task_defn = {
        "payload": {"push": push_payload, "dry_run": dry_run, "actions": actions},
        "metadata": {"source": "https://hg.mozilla.org/releases/mozilla-test-source" "/file/1b4ab9a276ce7bb217c02b83057586e7946860f9/taskcluster/ci/foobar"},
    }
    await gecko.do_actions({"work_dir": "foo"}, task_defn)
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

    mocker.patch.object(gecko, "vcs", new=vcs_mock)
    mocker.patch.object(gecko, "do_merge", new=mocked_do_merge)
    mocker.patch.object(gecko, "should_push", return_value=should_push)
    await gecko.perform_merge_actions({}, {}, actions, "/some/folder/here")
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

    mocker.patch.object(gecko, "vcs", new=vcs_mock)
    mocker.patch.object(gecko, "bump_version", new=mocked_bump)
    mocker.patch.object(gecko, "l10n_bump", new=mocked_l10n)
    await gecko.do_actions({"work_dir": "foo"}, {"metadata": {"source": "https://hg.mozilla.org/file/"}, "payload": {"push": True, "actions": actions}})
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

    mocker.patch.object(gecko, "vcs", new=vcs_mock)
    mocker.patch.object(gecko, "bump_version", new=mocked_bump)
    mocker.patch.object(gecko, "l10n_bump", new=mocked_l10n)
    with pytest.raises(TreeScriptError):
        await gecko.do_actions({"work_dir": "foo"}, {"metadata": {"source": "https://hg.mozilla.org/file/"}, "payload": {"push": False, "actions": actions}})


