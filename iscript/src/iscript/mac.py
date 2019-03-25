#!/usr/bin/env python
"""iscript mac signing/notarization functions."""
import arrow
import asyncio
import attr
from glob import glob
import logging
import os
import pexpect
import re

from scriptworker_client.aio import (
    raise_future_exceptions,
    retry_async,
    semaphore_wrapper,
)
from scriptworker_client.utils import (
    get_artifact_path,
    list_files,
    makedirs,
    rm,
    run_command,
)
from iscript.exceptions import (
    InvalidNotarization,
    IScriptError,
    TimeoutError,
    UnknownAppDir,
)

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
    """Track the various paths related to each app.

    Attributes:
        orig_path (str): the original path of the app tarball.
        parent_dir (str): the directory that contains the .app.
        app_path (str): the path to the .app directory.
        app_name (str): the basename of the .app directory.
        zip_path (str): the zipfile path for notarization, if we use the
            ``multi_account`` workflow.
        pkg_path (str): the unsigned .pkg path.
        notarization_log_path (str): the path to the logfile for notarization,
            if we use the ``multi_account`` workflow. This is currently
            overwritten each time we poll.
        target_tar_path: the path inside of ``artifact_dir`` for the signed
            and notarized tarball.
        target_pkg_path: the path inside of ``artifact_dir`` for the signed
            and notarized .pkg.

    """

    orig_path = attr.ib(default='')
    parent_dir = attr.ib(default='')
    app_path = attr.ib(default='')
    app_name = attr.ib(default='')
    zip_path = attr.ib(default='')
    pkg_path = attr.ib(default='')
    notarization_log_path = attr.ib(default='')
    target_tar_path = attr.ib(default='')
    target_pkg_path = attr.ib(default='')

    def check_required_attrs(self, required_attrs):
        """Make sure the ``required_attrs`` are set.

        Args:
            required_attrs (list): list of attribute strings

        Raises:
            IScriptError: on missing attr

        """
        for att in required_attrs:
            if not hasattr(self, att) or not getattr(self, att):
                raise IScriptError('Missing {} attr!'.format(att))


# set_app_path_and_name {{{1
def set_app_path_and_name(app):
    """Set the ``App`` ``app_path`` and ``app_name``.

    Because we might follow different workflows, we might not call ``sign``
    before ``create_pkg_files``. Let's move this logic into its own function.

    If ``app_path`` or ``app_name`` is already set, don't set them again.
    This is only to save some cycles.

    Args:
        app (App): the app to set.

    Raises:
        IScriptError: if ``parent_dir`` isn't set.

    """
    app.check_required_attrs(['parent_dir'])
    app.app_path = app.app_path or get_app_dir(app.parent_dir)
    app.app_name = app.app_name or os.path.basename(app.app_path)


# sign {{{1
async def sign(key_config, app, entitlements_path):
    """Sign the .app.

    Args:
        config (dict): the running config
        from_ (str): the tarfile path
        parent_dir (str): the top level directory to extract the app into
        key (str): the nick of the key to use to sign with

    Raises:
        IScriptError: on error.

    """
    set_app_path_and_name(app)
    await run_command(
        ['xattr', '-cr', app.app_name], cwd=app.parent_dir,
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
                run_command(
                    [
                        'codesign', '--force', '-o', 'runtime', '--verbose',
                        '--sign', key_config['identity'], '--entitlements',
                        entitlements_path, path
                    ],
                    cwd=app.parent_dir, exception=IScriptError
                )
            )
        ))
    await raise_future_exceptions(futures)

    # sign everything
    futures = []
    for path in list_files(app.app_path):
        if path in initial_files:
            continue
        futures.append(asyncio.ensure_future(
            semaphore_wrapper(
                semaphore,
                run_command(
                    [
                        'codesign', '--force', '-o', 'runtime', '--verbose',
                        '--sign', key_config['identity'], '--entitlements',
                        entitlements_path, path
                    ],
                    cwd=app.parent_dir, exception=IScriptError
                )
            )
        ))
    await raise_future_exceptions(futures)

    # sign bundle
    await run_command(
        [
            'codesign', '--force', '-o', 'runtime', '--verbose',
            '--sign', key_config['identity'], '--entitlements',
            entitlements_path, app.app_name
        ],
        cwd=app.parent_dir, exception=IScriptError
    )

    # verify bundle
    await run_command(
        [
            'codesign', '-vvv', '--deep', '--strict', app.app_name
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
        IScriptError: on failure
        TimeoutFailure: on timeout

    """
    log.info("Unlocking signing keychain {}".format(signing_keychain))
    child = pexpect.spawn('security', ['unlock-keychain', signing_keychain], encoding='utf-8')
    try:
        while True:
            index = await child.expect([pexpect.EOF, r"password to unlock {}: ".format(signing_keychain)], async_=True)
            if index == 0:
                break
            child.sendline(keychain_password)
    except (pexpect.exceptions.TIMEOUT) as exc:
        raise TimeoutError(
            "Timeout trying to unlock the keychain {}: {}!".format(signing_keychain, exc)
        ) from exc
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
    except KeyError as err:
        raise IScriptError('Unknown key config {} {}: {}'.format(config_key, key, err)) from err


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


# extract_all {{{1
async def extract_all_apps(work_dir, all_paths):
    """Extract all the apps into their own directories.

    Args:
        work_dir (str): the ``work_dir`` path
        all_paths (list): a list of ``App`` objects with their ``orig_path`` set

    Raises:
        IScriptError: on failure

    """
    log.info("Extracting all apps")
    futures = []
    for counter, app in enumerate(all_paths):
        app.check_required_attrs(['orig_path'])
        app.parent_dir = os.path.join(work_dir, str(counter))
        rm(app.parent_dir)
        makedirs(app.parent_dir)
        futures.append(asyncio.ensure_future(
            run_command(
                ['tar', 'xvf', app.orig_path], cwd=app.parent_dir,
                exception=IScriptError
            )
        ))
    await raise_future_exceptions(futures)


# create_all_app_zipfiles {{{1
async def create_all_app_zipfiles(all_paths):
    """Create notarization zipfiles for all the apps.

    Args:
        all_paths (list): list of ``App`` objects

    Raises:
        IScriptError: on failure

    """
    futures = []
    required_attrs = ['parent_dir', 'app_name']
    # zip up apps
    for app in all_paths:
        app.check_required_attrs(required_attrs)
        app.zip_path = os.path.join(
            app.parent_dir, "{}.zip".format(os.path.basename(app.parent_dir))
        )
        # ditto -c -k --norsrc --keepParent "${BUNDLE}" ${OUTPUT_ZIP_FILE}
        futures.append(asyncio.ensure_future(
            run_command(
                [
                    'zip', '-r', app.zip_path, app.app_name,
                ],
                cwd=app.parent_dir, exception=IScriptError,
            )
        ))
    await raise_future_exceptions(futures)


# create_one_app_zipfile {{{1
async def create_one_app_zipfile(work_dir, all_paths):
    """Create a single notarization zipfile for all the apps.

    Args:
        all_paths (list): list of ``App`` objects

    Raises:
        IScriptError: on failure

    Returns:
        str: the zip path

    """
    required_attrs = ['app_path']
    app_paths = []
    zip_path = os.path.join(work_dir, 'target.zip')
    for app in all_paths:
        app.check_required_attrs(required_attrs)
        app_paths.append(os.path.relpath(app.app_path, work_dir))
    await run_command(['zip', '-r', zip_path, *app_paths], cwd=work_dir, exception=IScriptError)
    return zip_path


# sign_all_apps {{{1
async def sign_all_apps(key_config, entitlements_path, all_paths):
    """Sign all the apps.

    Args:
        key_config (dict): the config for this signing key
        entitlements_path (str): the path to the entitlements file, used
            for signing
        all_paths (list): the list of ``App`` objects

    Raises:
        IScriptError: on failure

    """
    log.info("Signing all apps")
    futures = []
    for app in all_paths:
        futures.append(asyncio.ensure_future(
            sign(key_config, app, entitlements_path)
        ))
    await raise_future_exceptions(futures)


# get_bundle_id {{{1
def get_bundle_id(base_bundle_id, counter=None):
    """Get a bundle id for notarization.

    Args:
        base_bundle_id (str): the base string to use for the bundle id

    Returns:
        str: the bundle id

    """
    now = arrow.utcnow()
    # XXX we may want to encode more information in here. runId?
    bundle_id = "{}.{}.{}".format(
        base_bundle_id,
        os.environ.get('TASK_ID', 'None'),
        '{}{}'.format(now.timestamp, now.microsecond),
    )
    if counter:
        bundle_id = '{}.{}'.format(bundle_id, str(counter))
    return bundle_id


# get_uuid_from_log {{{1
def get_uuid_from_log(log_path):
    """Get the UUID from the notarization log.

    Args:
        log_path (str): the path to the log

    Raises:
        IScriptError: if we can't find the UUID

    Returns:
        str: the uuid

    """
    regex = re.compile(r'RequestUUID = (?P<uuid>[a-zA-Z0-9-]+)')
    try:
        with open(log_path, 'r') as fh:
            for line in fh.readlines():
                m = regex.search(line)
                if m:
                    return m['uuid']
    except OSError as err:
        raise IScriptError("Can't find UUID in {}: {}".format(log_path, err)) from err
    raise IScriptError("Can't find UUID in {}!".format(log_path))


# get_notarization_status_from_log {{{1
def get_notarization_status_from_log(log_path):
    """Get the status from the notarization log.

    Args:
        log_path (str): the path to the log file to parse

    Returns:
        str: either ``success`` or ``invalid``, depending on status
        None: if we have neither success nor invalid status

    """
    regex = re.compile(r'Status: (?P<status>success|invalid)')
    try:
        with open(log_path, 'r') as fh:
            contents = fh.read()
        m = regex.search(contents)
        if m is not None:
            return m['status']
    except OSError:
        pass


# wrap_notarization_with_sudo {{{1
async def wrap_notarization_with_sudo(config, key_config, all_paths):
    """Wrap the notarization requests with sudo.

    Apple creates a lockfile per user for notarization. To notarize concurrently,
    we use sudo against a set of accounts (``config['local_notarization_accounts']``).

    Raises:
        IScriptError: on failure

    Returns:
        dict: uuid to log path

    """
    futures = []
    accounts = config['local_notarization_accounts']
    counter = 0
    uuids = {}

    for app in all_paths:
        app.check_required_attrs(['zip_path', 'parent_dir'])

    while counter < len(all_paths):
        futures = []
        for account in accounts:
            app = all_paths[counter]
            app.notarization_log_path = os.path.join(app.parent_dir, 'notarization.log')
            bundle_id = get_bundle_id(key_config['base_bundle_id'], counter=str(counter))
            base_cmd = [
                'sudo', '-u', account,
                'xcrun', 'altool', '--notarize-app',
                '-f', app.zip_path,
                '--primary-bundle-id', bundle_id,
                '-u', key_config['apple_notarization_account'],
                '--password',
            ]
            log_cmd = base_cmd + ['********']
            futures.append(asyncio.ensure_future(
                retry_async(
                    run_command,
                    args=[base_cmd + [key_config['apple_notarization_password']]],
                    kwargs={
                        'log_path': app.notarization_log_path,
                        'log_cmd': log_cmd,
                        'exception': IScriptError,
                    },
                )
            ))
            counter += 1
            if counter >= len(all_paths):
                break
        await raise_future_exceptions(futures)
    for app in all_paths:
        uuids[get_uuid_from_log(app.notarization_log_path)] = app.notarization_log_path
    return uuids


# notarize_no_sudo {{{1
async def notarize_no_sudo(work_dir, key_config, zip_path):
    """Create a notarization request, without sudo, for a single zip.

    Raises:
        IScriptError: on failure

    Returns:
        dict: uuid to log path

    """
    notarization_log_path = os.path.join(work_dir, 'notarization.log')
    bundle_id = get_bundle_id(key_config['base_bundle_id'])
    base_cmd = [
        'xcrun', 'altool', '--notarize-app', '-f', zip_path,
        '--primary-bundle-id', bundle_id,
        '-u', key_config['apple_notarization_account'],
        '--password',
    ]
    log_cmd = base_cmd + ['********']
    await retry_async(
        run_command,
        args=[base_cmd + [key_config['apple_notarization_password']]],
        kwargs={
            'log_path': notarization_log_path,
            'log_cmd': log_cmd,
            'exception': IScriptError,
        },
    )
    uuids = {get_uuid_from_log(notarization_log_path): notarization_log_path}
    return uuids


# poll_notarization_uuid {{{1
async def poll_notarization_uuid(uuid, username, password, timeout, log_path, sleep_time=15):
    """Poll to see if the notarization for ``uuid`` is complete.

    Args:
        uuid (str): the uuid to poll for
        username (str): the apple user to poll with
        password (str): the apple password to poll with
        timeout (int): the maximum wait time
        sleep_time (int): the time to sleep between polling

    Raises:
        TimeoutError: on timeout
        InvalidNotarization: if the notarization fails with ``invalid``
        IScriptError: on unexpected failure

    """
    start = arrow.utcnow().timestamp
    timeout_time = start + timeout
    base_cmd = ['xcrun', 'altool', '--notarization-info', uuid, '-u', username, '--password']
    log_cmd = base_cmd + ['********']
    while 1:
        await retry_async(
            run_command,
            args=[base_cmd + [password]],
            kwargs={
                'log_path': log_path,
                'log_cmd': log_cmd,
                'exception': IScriptError,
            },
        )
        status = get_notarization_status_from_log(log_path)
        if status == 'success':
            break
        if status == 'invalid':
            raise InvalidNotarization('Invalid notarization for uuid {}!'.format(uuid))
        await asyncio.sleep(sleep_time)
        if arrow.utcnow().timestamp > timeout_time:
            raise TimeoutError("Timed out polling for uuid {}!".format(uuid))


# poll_all_notarization_status {{{1
async def poll_all_notarization_status(key_config, poll_uuids):
    """Poll all ``poll_uuids`` for status.

    Args:
        key_config (dict): the running config for this key
        poll_uuids (dict): uuid to ``log_path``

    Raises:
        IScriptError: on failure

    """
    log.info("Polling for notarization status")
    futures = []
    # We're going to overwrite the original notification log here.
    # If we want to preserve the logs, we should change this path
    for uuid, log_path in poll_uuids.items():
        futures.append(asyncio.ensure_future(
            poll_notarization_uuid(
                uuid, key_config['apple_notarization_account'],
                key_config['apple_notarization_password'],
                key_config['notarization_poll_timeout'],
                log_path, sleep_time=15
            )
        ))
    await raise_future_exceptions(futures)


# staple_apps {{{1
async def staple_apps(all_paths):
    """Staple the notarization results to each app.

    Args:
        all_paths (list): the list of App objects

    Raises:
        IScriptError: on failure

    """
    log.info("Stapling apps")
    futures = []
    for app in all_paths:
        app.check_required_attrs(['app_name', 'parent_dir'])
        futures.append(asyncio.ensure_future(
            run_command(
                ['xcrun', 'stapler', 'staple', '-v', app.app_name],
                cwd=app.parent_dir, exception=IScriptError
            )
        ))
    await raise_future_exceptions(futures)


# tar_apps {{{1
async def tar_apps(config, all_paths):
    """Create tar artifacts from the app directories.

    These tar artifacts will live in the ``artifact_dir``

    Args:
        config (dict): the running config
        all_paths (list): the App objects to tar up

    Raises:
        IScriptError: on failure

    """
    log.info("Tarring up artifacts")
    futures = []
    for app in all_paths:
        app.check_required_attrs(['app_name', 'orig_path', 'parent_dir'])
        # If we downloaded public/build/locale/target.tar.gz, then write to
        # artifact_dir/public/build/locale/target.tar.gz
        app.target_tar_path = '{}/public/{}'.format(
            config['artifact_dir'], app.orig_path.split('public/')[1]
        )
        makedirs(os.path.dirname(app.target_tar_path))
        # TODO: different tar commands based on suffix?
        futures.append(asyncio.ensure_future(
            run_command(
                ['tar', 'czvf', app.target_tar_path, app.app_name],
                cwd=app.parent_dir, exception=IScriptError,
            )
        ))
    await raise_future_exceptions(futures)


# create_pkg_files {{{1
async def create_pkg_files(key_config, all_paths):
    """Create .pkg installers from the .app files.

    Args:
        key_config (dict): the running config for this key
        all_paths: (list): the list of App objects to pkg

    Raises:
        IScriptError: on failure

    """
    log.info("Creating PKG files")
    futures = []
    for app in all_paths:
        # call set_app_path_and_name because we may not have called sign() earlier
        set_app_path_and_name(app)
        app.pkg_path = app.app_path.replace('.app', '.pkg')
        futures.append(asyncio.ensure_future(
            run_command(
                [
                    'sudo', 'pkgbuild', '--sign', key_config['pkg_cert_id'],
                    '--install-location', '/Applications', '--keychain',
                    key_config['signing_keychain'], '--component',
                    app.app_path, app.pkg_path
                ],
                cwd=app.parent_dir, exception=IScriptError
            )
        ))
    await raise_future_exceptions(futures)


# sign_pkg_files {{{1
async def sign_pkg_files(config, key_config, all_paths):
    """Sign the .pkg installers.

    These will be written into the ``artifact_dir``

    Args:
        config (dict): the running config
        key_config (dict): the running config for this key
        all_paths (list): the list of App objects to sign pkg for

    Raises:
        IScriptError: on failure

    """
    log.info("Signing pkgs")
    futures = []
    for app in all_paths:
        app.check_required_attrs(['parent_dir', 'orig_path'])
        app.target_pkg_path = '{}/public/{}'.format(
            config['artifact_dir'], app.orig_path.split('public/')[1]
        ).replace('.tar.gz', '.app')
        # passwords? keychain?
        futures.append(asyncio.ensure_future(
            run_command(
                [
                    'productsign', '--sign', key_config['pkg_cert_id'],
                    app.pkg_path, app.target_pkg_path
                ],
                cwd=app.parent_dir, exception=IScriptError
            )
        ))
    await raise_future_exceptions(futures)


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
    await extract_all_apps(work_dir, all_paths)
    await unlock_keychain(key_config['signing_keychain'], key_config['keychain_password'])
    await sign_all_apps(key_config, entitlements_path, all_paths)

    log.info("Notarizing")
    if key_config['notarize_type'] == 'multi_account':
        await create_all_app_zipfiles(all_paths)
        poll_uuids = await wrap_notarization_with_sudo(config, key_config, all_paths)
    else:
        zip_path = await create_one_app_zipfile(work_dir, all_paths)
        poll_uuids = await notarize_no_sudo(work_dir, key_config, zip_path)

    await poll_all_notarization_status(key_config, poll_uuids)
    await staple_apps(all_paths)
    await tar_apps(config, all_paths)
    await create_pkg_files(key_config, all_paths)
    # await sign_pkg_files(config, key_config, all_paths)

    log.info("Done signing and notarizing apps.")


# create_and_sign_all_pkg_files {{{1
async def create_and_sign_all_pkg_files(config, task):
    """Create and sign all pkg files for this task.

    Args:
        config (dict): the running configuration
        task (dict): the running task

    Raises:
        IScriptError: on fatal error.

    """
    work_dir = config['work_dir']

    # TODO get this from scopes?
    key = 'dep'
    key_config = get_key_config(config, key)

    all_paths = get_app_paths(config, task)
    await extract_all_apps(work_dir, all_paths)
    await unlock_keychain(key_config['signing_keychain'], key_config['keychain_password'])
    await create_pkg_files(key_config, all_paths)
    # await sign_pkg_files(config, key_config, all_paths)

    log.info("Done signing and notarizing apps.")
