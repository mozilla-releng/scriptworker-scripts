#!/usr/bin/env python
# coding=utf-8
"""Test iscript.mac
"""
from functools import partial
import mock
import os
import pexpect
import pytest
import iscript.mac as mac
from iscript.exceptions import IScriptError, TimeoutError, UnknownAppDir
from scriptworker_client.utils import makedirs


# helpers {{{1
async def noop_async(*args, **kwargs):
    pass


def touch(path):
    parent_dir = os.path.dirname(path)
    makedirs(parent_dir)
    with open(path, 'w') as fh:
        pass


# App {{{1
def test_app():
    """``App`` attributes can be set, and ``check_required_attrs`` raises if
    the required attrs aren't set.

    """
    a = mac.App()
    assert a.orig_path == ''
    a.orig_path = 'foo'
    assert a.orig_path == 'foo'
    a.check_required_attrs(['orig_path'])
    with pytest.raises(IScriptError):
        a.check_required_attrs(['app_path'])


# sign {{{1
@pytest.mark.asyncio
async def test_sign(mocker, tmpdir):
    """Render ``sign`` noop and verify we have complete code coverage.

    """
    config = {
        'mac_config': {
            'key': {
                'identity': 'id',
            },
        },
    }
    app = mac.App()
    app.parent_dir = str(tmpdir)
    entitlements_path = os.path.join(tmpdir, 'entitlements')
    app_path = os.path.join(tmpdir, 'foo.app')
    for p in list(mac.INITIAL_FILES_TO_SIGN) + ['Resources/MacOS/foo']:
        p = p.replace('*', 'foo')
        touch(os.path.join(app_path, p))
    mocker.patch.object(mac, 'run_command', new=noop_async)
    await mac.sign(config, app, 'key', entitlements_path)


# unlock_keychain {{{1
def fake_spawn(val, *args, **kwargs):
    return val


@pytest.mark.parametrize('results', ([1, 0], [0]))
@pytest.mark.asyncio
async def test_unlock_keychain_successful(results, mocker):
    """Mock a successful keychain unlock.

    """

    def fake_expect(*args, **kwargs):
        return results.pop(0)

    child = mocker.Mock()
    child.expect = fake_expect
    child.exitstatus = 0
    child.signalstatus = None
    mocker.patch.object(pexpect, 'spawn', new=partial(fake_spawn, child))
    await mac.unlock_keychain('x', 'y')


@pytest.mark.asyncio
async def test_unlock_keychain_timeout(mocker):
    """``unlock_keychain`` raises a ``TimeoutError`` on pexpect timeout.

    """

    def fake_expect(*args, **kwargs):
        raise pexpect.exceptions.TIMEOUT('foo')

    child = mocker.Mock()
    child.expect = fake_expect
    child.exitstatus = 0
    child.signalstatus = None
    mocker.patch.object(pexpect, 'spawn', new=partial(fake_spawn, child))
    with pytest.raises(TimeoutError):
        await mac.unlock_keychain('x', 'y')


@pytest.mark.asyncio
async def test_unlock_keychain_failure(mocker):
    """``unlock_keychain`` throws an ``IScriptError`` on non-zero exit status.

    """
    results = [0]

    def fake_expect(*args, **kwargs):
        return results.pop(0)

    child = mocker.Mock()
    child.expect = fake_expect
    child.exitstatus = 1
    child.signalstatus = None
    mocker.patch.object(pexpect, 'spawn', new=partial(fake_spawn, child))
    with pytest.raises(IScriptError):
        await mac.unlock_keychain('x', 'y')


# get_app_dir {{{1
@pytest.mark.parametrize('apps, raises', ((
    [], True,
), (
    ['foo.app'], False,
), (
    ['foo.notanapp'], True,
), (
    ['one.app', 'two.app'], True,
)))
def test_get_app_dir(tmpdir, apps, raises):
    """``get_app_dir`` returns the single ``.app`` dir in ``parent_dir``, and
    raises ``UnknownAppDir`` if there is greater or fewer than one ``.app``.

    """
    for app in apps:
        os.makedirs(os.path.join(tmpdir, app))

    if raises:
        with pytest.raises(UnknownAppDir):
            mac.get_app_dir(tmpdir)
    else:
        assert mac.get_app_dir(tmpdir) == os.path.join(tmpdir, apps[0])


# get_key_config {{{1
@pytest.mark.parametrize('key, config_key, raises', ((
    'dep', 'mac_config', False
), (
    'nightly', 'mac_config', False
), (
    'invalid_key', 'mac_config', True
), (
    'dep', 'invalid_config_key', True
)))
def test_get_config_key(key, config_key, raises):
    """``get_config_key`` returns the correct subconfig.

    """
    config = {
        'mac_config': {
            'dep': {
                'key': 'dep',
            },
            'nightly': {
                'key': 'nightly',
            },
        },
    }
    if raises:
        with pytest.raises(IScriptError):
            mac.get_key_config(config, key, config_key=config_key)
    else:
        assert mac.get_key_config(config, key, config_key=config_key) == config[config_key][key]


# get_app_paths {{{1
def test_get_app_paths():
    """``get_app_paths`` creates ``App`` objects with ``orig_path`` set to
    the cot-downloaded artifact paths.

    """
    config = {'work_dir': 'work'}
    task = {
        'payload': {
            'upstreamArtifacts': [{
                'paths': ['public/foo'],
                'taskId': 'task1',
            }, {
                'paths': ['public/bar', 'public/baz'],
                'taskId': 'task2',
            }],
        }
    }
    paths = []
    apps = mac.get_app_paths(config, task)
    for app in apps:
        assert isinstance(app, mac.App)
        paths.append(app.orig_path)
    assert paths == [
        'work/cot/task1/public/foo', 'work/cot/task2/public/bar',
        'work/cot/task2/public/baz'
    ]


# extract_all_apps {{{1
@pytest.mark.parametrize('raises', (True, False))
@pytest.mark.asyncio
async def test_extract_all_apps(mocker, raises, tmpdir):
    """``extract_all_apps`` creates ``parent_dir`` and raises if any tar command
    fails.

    """

    async def fake_run_command(*args, **kwargs):
        if raises:
            raise IScriptError('foo')

    mocker.patch.object(mac, 'run_command', new=fake_run_command)
    work_dir = os.path.join(str(tmpdir), 'work')
    all_paths = [
        mac.App(orig_path=os.path.join(work_dir, 'orig1')),
        mac.App(orig_path=os.path.join(work_dir, 'orig2')),
        mac.App(orig_path=os.path.join(work_dir, 'orig3')),
    ]
    if raises:
        with pytest.raises(IScriptError):
            await mac.extract_all_apps(work_dir, all_paths)
    else:
        await mac.extract_all_apps(work_dir, all_paths)
        for i in ('0', '1', '2'):
            assert os.path.isdir(os.path.join(work_dir, i))
