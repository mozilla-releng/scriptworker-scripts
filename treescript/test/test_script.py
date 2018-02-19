import json
import mock
import os
import pytest
import sys

import scriptworker.client
from scriptworker.exceptions import ScriptWorkerTaskException, ScriptWorkerException
from treescript.test import noop_async, noop_sync, read_file, tmpdir, BASE_DIR
import treescript.script as script

assert tmpdir  # silence flake8

# helper constants, fixtures, functions {{{1
EXAMPLE_CONFIG = os.path.join(BASE_DIR, 'config_example.json')


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


# TreeContext {{{1
def test_tree_context():
    c = script.TreeContext()
    c.write_json()


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
    mocker.patch.object(script, 'validate_task_schema', new=noop_sync)
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


# get_default_config {{{1
def test_get_default_config():
    parent_dir = os.path.dirname(os.getcwd())
    c = script.get_default_config()
    assert c['work_dir'] == os.path.join(parent_dir, 'work_dir')


# usage {{{1
def test_usage():
    with pytest.raises(SystemExit):
        script.usage()


# main {{{1
def test_main_missing_args(mocker):
    mocker.patch.object(sys, 'argv', new=[__file__])
    with pytest.raises(SystemExit):
        script.main()


def test_main_argv(tmpdir, mocker):
    conf_file = get_conf_file(tmpdir, verbose=False, ssl_cert=None)
    mocker.patch.object(sys, 'argv', new=[__file__, conf_file])
    mocker.patch.object(script, 'async_main', new=noop_async)
    script.main()


def test_main_noargv(tmpdir, mocker):
    conf_file = get_conf_file(tmpdir, verbose=True)
    mocker.patch.object(script, 'async_main', new=die_async)
    with pytest.raises(SystemExit):
        script.main(config_path=conf_file)


# do_actions {{{1
@pytest.mark.asyncio
async def test_do_actions(mocker):
    actions = ["foo:bar:tagging", "foo:bar:version_bump"]
    called_tag = [False]
    called_bump = [False]

    async def mocked_tag(*args, **kwargs):
        called_tag[0] = True

    async def mocked_bump(*args, **kwargs):
        called_bump[0] = True

    mocker.patch.object(script, 'do_tagging', new=mocked_tag)
    mocker.patch.object(script, 'bump_version', new=mocked_bump)
    mocker.patch.object(script, 'log_outgoing', new=noop_async)
    await script.do_actions(script.Context(), actions, directory='/some/folder/here')
    assert called_tag[0]
    assert called_bump[0]


@pytest.mark.asyncio
async def test_do_actions_unknown(mocker):
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
        await script.do_actions(script.Context(), actions, directory='/some/folder/here')
    assert called_tag[0] is False
    assert called_bump[0] is False
