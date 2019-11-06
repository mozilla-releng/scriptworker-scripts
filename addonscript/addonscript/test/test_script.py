# noqa
import json
import os
from unittest.mock import MagicMock

import mock
import pytest
import scriptworker.client
from scriptworker.context import Context
from scriptworker.exceptions import ScriptWorkerException, ScriptWorkerTaskException

# from treescript.test import noop_async, noop_sync, read_file, tmpdir, BASE_DIR
import addonscript.script as script

# assert tmpdir  # silence flake8

# helper constants, fixtures, functions {{{1
# EXAMPLE_CONFIG = os.path.join(BASE_DIR, 'config_example.json')

"""
@pytest.fixture(scope='function')
def context():
    return Context()


def get_conf_file(tmpdir, **kwargs):
    conf = json.loads(read_file(EXAMPLE_CONFIG))
    conf.update(kwargs)
    conf['work_dir'] = os.path.join(tmpdir, 'work')
    conf['artifact_dir'] = os.path.join(tmpdir, 'artifact')
    path = os.path.join(tmpdir, "new_config.json")
    with open(path, "w") as fh:
        json.dump(conf, fh)
    return path


async def die_async(*args, **kwargs):
    raise ScriptWorkerTaskException("Expected exception.")


# async_main {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    'robustcheckout_works,raises,actions',
    ((
        False, ScriptWorkerException, ["foo:bar:some_action"]
    ), (
        True, None, ["foo:bar:some_action"]
    ), (
        True, None, None
    ))
)
async def test_async_main(tmpdir, mocker, robustcheckout_works, raises, actions):

    async def fake_validate_robustcheckout(_):
        return robustcheckout_works

    def action_fun(*args, **kwargs):
        return actions

    mocker.patch.object(scriptworker.client, 'get_task', new=noop_sync)
    mocker.patch.object(script, 'task_action_types', new=action_fun)
    mocker.patch.object(script, 'validate_robustcheckout_works', new=fake_validate_robustcheckout)
    mocker.patch.object(script, 'log_mercurial_version', new=noop_async)
    mocker.patch.object(script, 'checkout_repo', new=noop_async)
    mocker.patch.object(script, 'do_actions', new=noop_async)
    context = mock.MagicMock()
    if raises:
        with pytest.raises(raises):
            await script.async_main(context)
    else:
        await script.async_main(context)


# do_actions {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize(
    'push_scope,dry_run,push_expect_called',
    (
        (['foo:bar:push'], True, False),
        (['foo:bar:push'], False, True),
        ([], False, False),
        ([], True, False),
    )
)
async def test_do_actions(mocker, context, push_scope, dry_run, push_expect_called):
    actions = ["foo:bar:tagging", "foo:bar:version_bump"]
    actions += push_scope
    called_tag = [False]
    called_bump = [False]
    called_push = [False]

    async def mocked_tag(*args, **kwargs):
        called_tag[0] = True

    async def mocked_bump(*args, **kwargs):
        called_bump[0] = True

    async def mocked_push(*args, **kwargs):
        called_push[0] = True

    mocker.patch.object(script, 'do_tagging', new=mocked_tag)
    mocker.patch.object(script, 'bump_version', new=mocked_bump)
    mocker.patch.object(script, 'push', new=mocked_push)
    mocker.patch.object(script, 'log_outgoing', new=noop_async)
    mocker.patch.object(script, 'is_dry_run').return_value = dry_run
    await script.do_actions(context, actions, directory='/some/folder/here')
    assert called_tag[0]
    assert called_bump[0]
    assert called_push[0] is push_expect_called


@pytest.mark.asyncio
async def test_do_actions_unknown(mocker, context):
    actions = ["foo:bar:unknown"]
    called_tag = [False]
    called_bump = [False]

    async def mocked_tag(*args, **kwargs):
        called_tag[0] = True

    async def mocked_bump(*args, **kwargs):
        called_bump[0] = True

    mocker.patch.object(script, 'do_tagging', new=mocked_tag)
    mocker.patch.object(script, 'bump_version', new=mocked_bump)
    mocker.patch.object(script, 'log_outgoing', new=noop_async)
    with pytest.raises(NotImplementedError):
        await script.do_actions(context, actions, directory='/some/folder/here')
    assert called_tag[0] is False
    assert called_bump[0] is False

"""
