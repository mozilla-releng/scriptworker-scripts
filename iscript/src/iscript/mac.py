#!/usr/bin/env python
"""Signingscript task functions."""
import asyncio
import attr
from glob import glob
import logging
import os
import pexpect

from scriptworker_client.utils import (
    extract_tarball,
    get_artifact_path,
    list_files,
    makedirs,
    rm,
    run_command,
)
from iscript.utils import (
    create_zipfile,
    raise_future_exceptions,
    semaphore_wrapper,
)
from iscript.exceptions import IScriptError, UnknownAppDir

log = logging.getLogger(__name__)


INITIAL_FILES_TO_SIGN = (
    'Contents/MacOS/XUL',
    'Contents/MacOS/pingsender',
    'Contents/MacOS/*.dylib',
    'Contents/MacOS/crashreporter.app/Contents/MacOS/minidump-analyzer',
    'Contents/MacOS/crashreporter.app/Contents/MacOS/crashreporter',
    'Contents/MacOS/firefox-bin',
    'Contents/MacOS/plugin-container.app/Contents/MacOS/plugin-container',
    'Contents/MacOS/updater.app/Contents/MacOS/org.mozilla.updater',
    'Contents/MacOS/firefox',
)


@attr.s
class App(object):
    orig_path = attr.ib(default='')
    parent_dir = attr.ib(default='')
    app_path = attr.ib(default='')
    zip_path = attr.ib(default='')


# sign {{{1
async def sign(config, app, key, entitlements_path):
    """Sign the .app.

    Args:
        config (dict): the running config
        from_ (str): the tarfile path
        parent_dir (str): the top level directory to extract the app into
        key (str): the nick of the key to use to sign with

    Raises:
        IScriptError: on error.

    """
    key_config = get_key_config(config, key)
    app.app_path = get_app_dir(app.parent_dir)
    await run_command(
        ['xattr', '-cr', app.app_path], cwd=app.parent_dir,
        exception=IScriptError
    )
    # find initial files from INITIAL_FILES_TO_SIGN globs
    initial_files = []
    for path in INITIAL_FILES_TO_SIGN:
        initial_files.extend(glob(os.path.join(app.app_path, path)))

    # sign initial files
    futures = []
    semaphore = asyncio.Semaphore(10)
    for path in initial_files:
        futures.append(asyncio.ensure_future(
            semaphore_wrapper(
                semaphore,
                run_command,
                [
                    'codesign', '--force', '-o', 'runtime', '--verbose',
                    '--sign', key_config['identity'], '--entitlements',
                    entitlements_path, path
                ],
                cwd=app.parent_dir, exception=IScriptError
            )
        ))
    await raise_future_exceptions(futures)

    # sign everything
    futures = []
    for path in list_files(app.app_path):
        if path in initial_files:
            continue
        futures.append(
            semaphore_wrapper(
                semaphore,
                run_command,
                [
                    'codesign', '--force', '-o', 'runtime', '--verbose',
                    '--sign', key_config['identity'], '--entitlements',
                    entitlements_path, path
                ],
                cwd=app.parent_dir, exception=IScriptError
            )
        )
    await raise_future_exceptions(futures)

    # sign bundle
    await run_command(
        [
            'codesign', '--force', '-o', 'runtime', '--verbose',
            '--sign', key_config['identity'], '--entitlements',
            entitlements_path, app.app_path
        ],
        cwd=app.parent_dir, exception=IScriptError
    )

    # verify bundle
    await run_command(
        [
            'codesign', '-vvv', '--deep', '--strict', app.app_path
        ],
        cwd=app.parent_dir, exception=IScriptError
    )


# unlock_keychain {{{1
async def unlock_keychain(signing_keychain, keychain_password):
    """Unlock the signing keychain.

    Args:
        signing_keychain (str): the path to the signing keychain
        keychain_password (str): the keychain password

    Raises:
        IScriptError: on timeout or failure

    """
    child = pexpect.spawn('security', ['unlock-keychain', signing_keychain], encoding='utf-8')
    try:
        while True:
            index = child.expect([pexpect.EOF, r"password to unlock.*: "], async_=True)
            if index == 0:
                break
            child.sendline(b'keychain_password')
    except (pexpect.exceptions.TIMEOUT) as exc:
        raise IScriptError("Timeout trying to unlock the keychain {}: {}!".format(signing_keychain, exc))
    child.close()
    if child.exitstatus != 0 or child.signalstatus is not None:
        raise IScriptError(
            "Failed unlocking {}! exit {} signal {}".format(
                signing_keychain, child.exitstatus, child.signalstatus
            )
        )


# get_app_dir {{{1
def get_app_dir(parent_dir):
    """Get the .app directory in a ``parent_dir``.

    This assumes there is one, and only one, .app directory in ``parent_dir``.

    Args:
        parent_dir (str): the parent directory path

    Raises:
        UnknownAppDir: if there is no single app dir

    """
    apps = glob('{}/*.app'.format(parent_dir))
    if len(apps) != 1:
        raise UnknownAppDir("Can't find a single .app in {}: {}".format(
            parent_dir, apps
        ))
    return apps[0]


# get_key_config {{{1
def get_key_config(config, key, config_key='mac_config'):
    """Get the key subconfig from ``config``.

    Args:
        config (dict): the running config
        key (str): the key nickname, e.g. ``dep``
        config_key (str): the config key to use, e.g. ``mac_config``

    Raises:
        IScriptError: on invalid ``key`` or ``config_key``

    Returns:
        dict: the subconfig for the given ``config_key`` and ``key``

    """
    try:
        return config[config_key][key]
    except KeyError as e:
        raise IScriptError('Unknown key config {} {}: {}'.format(config_key, key, e))


# get_app_paths {{{1
def get_app_paths(config, task):
    """Create a list of ``App`` objects from the task.

    These will have their ``orig_path`` set.

    Args:
        config (dict): the running config
        task (dict): the running task

    Returns:
        list: a list of App objects

    """
    all_paths = []
    for upstream_artifact_info in task['payload']['upstreamArtifacts']:
        for subpath in upstream_artifact_info['paths']:
            orig_path = get_artifact_path(
                upstream_artifact_info['taskId'], subpath, work_dir=config['work_dir'],
            )
            all_paths.append(App(orig_path=orig_path))
    return all_paths


# sign_and_notarize_all {{{1
async def sign_and_notarize_all(config, task):
    """Sign and notarize all mac apps for this task.

    Args:
        config (dict): the running configuration
        task (dict): the running task

    Raises:
        IScriptError: on fatal error.

    """
    work_dir = config['work_dir']
    # TODO get entitlements -- default or from url
    entitlements_path = os.path.join(work_dir, "browser.entitlements.txt")

    # TODO get this from scopes?
    key = 'dep'
    key_config = get_key_config(config, key)

    all_paths = get_app_paths(config, task)

    # extract
    futures = []
    for counter, app in enumerate(all_paths):
        app.parent_dir = os.path.join(work_dir, str(counter))
        rm(app.parent_dir)
        makedirs(app.parent_dir)
        futures.append(asyncio.ensure_future(
            extract_tarball(app.orig_path, app.parent_dir)
        ))
    await raise_future_exceptions(futures)

    # sign
    await unlock_keychain(key_config['signing_keychain'], key_config['keychain_password'])
    futures = []
    for app in all_paths:
        futures.append(asyncio.ensure_future(
            sign(key_config, app, entitlements_path)
        ))
    await raise_future_exceptions(futures)

    poll_uuids = []
    if key_config['notarize_type'] == 'multi_account':
        futures = []
        for app in all_paths:
            app.zip_path = os.path.join(
                app.parent_dir, "{}.zip".format(os.path.basename(app.parent_dir))
            )
            # ditto -c -k --norsrc --keepParent "${BUNDLE}" ${OUTPUT_ZIP_FILE}
            futures.append(asyncio.ensure_future(
                create_zipfile(
                    app.zip_path, app.app_path, app.parent_dir,
                )
            ))
        await raise_future_exceptions(futures)

        for app in all_paths:
            # notarize, concurrent across `local_notarization_accounts`
            # sudo
            pass

    for app in all_paths:
        pass
        # poll

    if key_config['notarize_type'] == 'multi_account':
        for app in all_paths:
            # staple
            pass
    # tar up the app_dir, into artifact_dir
