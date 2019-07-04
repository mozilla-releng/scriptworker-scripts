#!/usr/bin/env python
"""iscript mac signing/notarization functions."""
import arrow
import asyncio
import attr
from copy import deepcopy
from glob import glob
import logging
import os
import pexpect
import plistlib
import re
import shlex
from shutil import copy2

from scriptworker_client.aio import (
    download_file,
    raise_future_exceptions,
    retry_async,
    semaphore_wrapper,
)
from scriptworker_client.exceptions import DownloadError
from scriptworker_client.utils import get_artifact_path, makedirs, rm, run_command
from iscript.exceptions import (
    InvalidNotarization,
    IScriptError,
    TimeoutError,
    UnknownAppDir,
)
from iscript.util import get_key_config

from iscript.autograph import sign_omnija_with_autograph, sign_widevine_dir

log = logging.getLogger(__name__)


MAC_DESIGNATED_REQUIREMENTS = (
    """=designated => ( """
    """(anchor apple generic and certificate leaf[field.1.2.840.113635.100.6.1.9] ) """
    """or (anchor apple generic and certificate 1[field.1.2.840.113635.100.6.2.6] """
    """and certificate leaf[field.1.2.840.113635.100.6.1.13] and certificate """
    """leaf[subject.OU] = "%(subject_ou)s"))"""
)

KNOWN_ARTIFACT_PREFIXES = ("public/", "releng/partner/")


# App {{{1
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
        pkg_name (str): the basename of the .pkg path.
        notarization_log_path (str): the path to the logfile for notarization,
            if we use the ``multi_account`` workflow. This is currently
            overwritten each time we poll.
        target_tar_path (str): the path inside of ``artifact_dir`` for the signed
            and notarized tarball.
        target_pkg_path (str): the path inside of ``artifact_dir`` for the signed
            and notarized .pkg.
        formats (list): the list of formats to sign with.

    """

    orig_path = attr.ib(default="")
    parent_dir = attr.ib(default="")
    app_path = attr.ib(default="")
    app_name = attr.ib(default="")
    zip_path = attr.ib(default="")
    pkg_path = attr.ib(default="")
    pkg_name = attr.ib(default="")
    notarization_log_path = attr.ib(default="")
    target_tar_path = attr.ib(default="")
    target_pkg_path = attr.ib(default="")
    formats = attr.ib(default="")
    artifact_prefix = attr.ib(default="")

    def check_required_attrs(self, required_attrs):
        """Make sure the ``required_attrs`` are set.

        Args:
            required_attrs (list): list of attribute strings

        Raises:
            IScriptError: on missing attr

        """
        for att in required_attrs:
            if not hasattr(self, att) or not getattr(self, att):
                raise IScriptError("Missing {} attr!".format(att))


# tar helpers {{{1
def _get_tar_create_options(path):
    base_opts = "c"
    if path.endswith(".tar.gz"):
        return "{}zf".format(base_opts)
    elif path.endswith(".tar.bz2"):
        return "{}jf".format(base_opts)
    else:
        raise IScriptError("Unknown tarball suffix in path {}".format(path))


def _get_pkg_name_from_tarball(path):
    for ext in (".tar.gz", ".tar.bz2", ".dmg"):
        if path.endswith(ext):
            return path.replace(ext, ".pkg")
    raise IScriptError("Unknown tarball suffix in path {}".format(path))


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
    app.check_required_attrs(["parent_dir"])
    app.app_path = app.app_path or get_app_dir(app.parent_dir)
    app.app_name = app.app_name or os.path.basename(app.app_path)


# get_bundle_executable {{{1
def get_bundle_executable(appdir):
    """Return the CFBundleIdentifier from a Mac application.

    Args:
        appdir (str): the path to the app

    Returns:
        str: the CFBundleIdentifier

    Raises:
        InvalidFileException: on ``plistlib.load`` error
        KeyError: if the plist doesn't include ``CFBundleIdentifier``

    """
    return plistlib.readPlist(os.path.join(appdir, "Contents", "Info.plist"))[
        "CFBundleExecutable"
    ]


# _get_sign_command {{{1
def _get_sign_command(identity, keychain):
    return [
        "codesign",
        "-s",
        identity,
        "-fv",
        "--keychain",
        keychain,
        "--requirement",
        MAC_DESIGNATED_REQUIREMENTS % {"subject_ou": identity},
    ]


# sign_geckodriver {{{1
async def sign_geckodriver(config, key_config, all_paths):
    """Sign geckodriver.

    Args:
        key_config (dict): the running config
        all_paths (list): list of App objects

    Raises:
        IScriptError: on error.

    """
    identity = key_config["identity"]
    keychain = key_config["signing_keychain"]
    sign_command = _get_sign_command(identity, keychain)

    for app in all_paths:
        app.check_required_attrs(["orig_path", "parent_dir", "artifact_prefix"])
        app.target_tar_path = "{}/{}{}".format(
            config["artifact_dir"],
            app.artifact_prefix,
            app.orig_path.split(app.artifact_prefix)[1],
        )
        file_ = "geckodriver"
        if not os.path.exists(os.path.join(app.parent_dir, file_)):
            raise IScriptError(f"No such file {file_}!")
        await retry_async(
            run_command,
            args=[sign_command + [file_]],
            kwargs={
                "cwd": app.parent_dir,
                "exception": IScriptError,
                "output_log_on_exception": True,
            },
            retry_exceptions=(IScriptError,),
        )
        env = deepcopy(os.environ)
        # https://superuser.com/questions/61185/why-do-i-get-files-like-foo-in-my-tarball-on-os-x
        env["COPYFILE_DISABLE"] = "1"
        await run_command(
            [
                "tar",
                _get_tar_create_options(app.target_tar_path),
                app.target_tar_path,
                file_,
            ],
            cwd=app.parent_dir,
            env=env,
            exception=IScriptError,
        )


# sign_app {{{1
async def sign_app(key_config, app_path, entitlements_path):
    """Sign the .app.

    Largely taken from build-tools' ``dmg_signfile``.

    Args:
        key_config (dict): the running config
        app_path (str): the path to the app to be signed (extracted)
        entitlements_path (str): the path to the entitlements file for signing

    Raises:
        IScriptError: on error.

    """
    SIGN_DIRS = ("MacOS", "Library")
    parent_dir = os.path.dirname(app_path)
    app_name = os.path.basename(app_path)
    await run_command(
        ["xattr", "-cr", app_name], cwd=parent_dir, exception=IScriptError
    )
    identity = key_config["identity"]
    keychain = key_config["signing_keychain"]
    sign_command = _get_sign_command(identity, keychain)

    if key_config.get("sign_with_entitlements", False):
        sign_command.extend(["-o", "runtime", "--entitlements", entitlements_path])

    app_executable = get_bundle_executable(app_path)
    app_path_len = len(app_path)
    contents_dir = os.path.join(app_path, "Contents")
    for top_dir, dirs, files in os.walk(contents_dir):
        for dir_ in dirs:
            abs_dir = os.path.join(top_dir, dir_)
            if top_dir == contents_dir and dir_ not in SIGN_DIRS:
                log.debug("Skipping %s because it's not in SIGN_DIRS.", abs_dir)
                dirs.remove(dir_)
                continue
            if dir_.endswith(".app"):
                await sign_app(key_config, abs_dir, entitlements_path)
        if top_dir == contents_dir:
            log.debug(
                "Skipping file iteration in %s because it's the root directory.",
                top_dir,
            )
            continue

        for file_ in files:
            abs_file = os.path.join(top_dir, file_)
            # Deal with inner .app's above, not here.
            if top_dir[app_path_len:].count(".app") > 0:
                log.debug("Skipping %s because it's part of an inner app.", abs_file)
            # app_executable gets signed with the outer package.
            if file_ == app_executable:
                log.debug("Skipping %s because it's the main executable.", abs_file)
                continue
            dir_ = os.path.dirname(abs_file)
            await retry_async(
                run_command,
                args=[sign_command + [file_]],
                kwargs={
                    "cwd": dir_,
                    "exception": IScriptError,
                    "output_log_on_exception": True,
                },
                retry_exceptions=(IScriptError,),
            )

    await sign_libclearkey(contents_dir, sign_command, app_path)

    # sign bundle
    await retry_async(
        run_command,
        args=[sign_command + [app_name]],
        kwargs={
            "cwd": parent_dir,
            "exception": IScriptError,
            "output_log_on_exception": True,
        },
        retry_exceptions=(IScriptError,),
    )


async def sign_libclearkey(contents_dir, sign_command, app_path):
    """Sign libclearkey if it exists.

    Special case Contents/Resources/gmp-clearkey/0.1/libclearkey.dylib
    which is living in the wrong place (bug 1100450), but isn't trivial to move.
    Only do this for the top level app and not nested apps

    Args:
        contents_dir (str): the ``Contents/`` directory path
        sign_command (list): the command to sign with
        app_path (str): the path to the .app dir

    Raises:
        IScriptError: on failure

    """
    if "Contents/" not in app_path:
        dir_ = os.path.join(contents_dir, "Resources/gmp-clearkey/0.1/")
        file_ = "libclearkey.dylib"
        if os.path.exists(os.path.join(dir_, file_)):
            await retry_async(
                run_command,
                args=[sign_command + [file_]],
                kwargs={
                    "cwd": dir_,
                    "exception": IScriptError,
                    "output_log_on_exception": True,
                },
                retry_exceptions=(IScriptError,),
            )


# verify_app_signature {{{1
async def verify_app_signature(key_config, app):
    """Verify the app signature.

    Args:
        key_config (dict): the config for this signing key
        app (App): the app to verify

    Raises:
        IScriptError: on failure

    """
    if not key_config.get("verify_mac_signature", True):
        return
    required_attrs = ["parent_dir", "app_path"]
    app.check_required_attrs(required_attrs)
    await run_command(
        ["codesign", "-vvv", "--deep", "--strict", app.app_path],
        cwd=app.parent_dir,
        exception=IScriptError,
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
    child = pexpect.spawn(
        "security", ["unlock-keychain", signing_keychain], encoding="utf-8"
    )
    try:
        while True:
            index = await child.expect(
                [pexpect.EOF, r"password to unlock {}: ".format(signing_keychain)],
                async_=True,
            )
            if index == 0:
                break
            child.sendline(keychain_password)
    except (pexpect.exceptions.TIMEOUT) as exc:
        raise TimeoutError(
            "Timeout trying to unlock the keychain {}: {}!".format(
                signing_keychain, exc
            )
        ) from exc
    child.close()
    if child.exitstatus != 0 or child.signalstatus is not None:
        raise IScriptError(
            "Failed unlocking {}! exit {} signal {}".format(
                signing_keychain, child.exitstatus, child.signalstatus
            )
        )


async def update_keychain_search_path(config, signing_keychain):
    """Add the signing keychain to the keychain search path.

    Mac signing is failing without this, and works with it. In addition, if we
    add both nightly and release keychains to the search path simultaneously,
    duplicate key IDs break signing. Instead, let's run ``security
    list-keychains -s`` every time, to make sure it's populated with the right
    keychains.

    Args:
        config (dict): the running config
        signing_keychain (str): the path to the signing keychain

    Raises:
        IScriptError: on failure

    """
    await run_command(
        ["security", "list-keychains", "-s", signing_keychain]
        + config.get(
            "default_keychains",
            [
                f"{os.environ['HOME']}/Library/Keychains/login.keychain-db",
                "/Library/Keychains/System.keychain",
            ],
        ),
        cwd=config["work_dir"],
        exception=IScriptError,
    )


# get_app_dir {{{1
def get_app_dir(parent_dir):
    """Get the .app directory in a ``parent_dir``.

    This assumes there is one, and only one, .app directory in ``parent_dir``,
    though it can be in a subdirectory.

    Args:
        parent_dir (str): the parent directory path

    Raises:
        UnknownAppDir: if there is no single app dir

    """
    apps = glob("{}/*.app".format(parent_dir)) + glob("{}/*/*.app".format(parent_dir))
    if len(apps) != 1:
        raise UnknownAppDir(
            "Can't find a single .app in {}: {}".format(parent_dir, apps)
        )
    return apps[0]


# get_app_paths {{{1
def _get_artifact_prefix(path):
    for prefix in KNOWN_ARTIFACT_PREFIXES:
        if path.startswith(prefix):
            return prefix
    raise IScriptError(f"Unknown artifact prefix for {path}!")


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
    for upstream_artifact_info in task["payload"]["upstreamArtifacts"]:
        for subpath in upstream_artifact_info["paths"]:
            orig_path = get_artifact_path(
                upstream_artifact_info["taskId"], subpath, work_dir=config["work_dir"]
            )
            all_paths.append(
                App(
                    orig_path=orig_path,
                    formats=upstream_artifact_info["formats"],
                    artifact_prefix=_get_artifact_prefix(subpath),
                )
            )
    return all_paths


# extract_all_apps {{{1
async def extract_all_apps(config, all_paths):
    """Extract all the apps into their own directories.

    Args:
        work_dir (str): the ``work_dir`` path
        all_paths (list): a list of ``App`` objects with their ``orig_path`` set

    Raises:
        IScriptError: on failure

    """
    log.info("Extracting all apps")
    futures = []
    work_dir = config["work_dir"]
    unpack_dmg = os.path.join(os.path.dirname(__file__), "data", "unpack-diskimage")
    for counter, app in enumerate(all_paths):
        app.check_required_attrs(["orig_path"])
        app.parent_dir = os.path.join(work_dir, str(counter))
        rm(app.parent_dir)
        makedirs(app.parent_dir)
        if app.orig_path.endswith((".tar.bz2", ".tar.gz", ".tgz")):
            futures.append(
                asyncio.ensure_future(
                    run_command(
                        ["tar", "xf", app.orig_path],
                        cwd=app.parent_dir,
                        exception=IScriptError,
                    )
                )
            )
        elif app.orig_path.endswith(".dmg"):
            unpack_mountpoint = os.path.join(
                "/tmp", f"{config.get('dmg_prefix', 'dmg')}-{counter}-unpack"
            )
            futures.append(
                asyncio.ensure_future(
                    run_command(
                        [unpack_dmg, app.orig_path, unpack_mountpoint, app.parent_dir],
                        cwd=app.parent_dir,
                        exception=IScriptError,
                        log_level=logging.DEBUG,
                    )
                )
            )
        else:
            raise IScriptError(f"unknown file type {app.orig_path}")
    await raise_future_exceptions(futures)
    if app.orig_path.endswith(".dmg"):
        # nuke the softlink to /Applications
        for counter, app in enumerate(all_paths):
            rm(os.path.join(app.parent_dir, " "))


# create_all_notarization_zipfiles {{{1
async def create_all_notarization_zipfiles(all_paths, path_attr="app_path"):
    """Create notarization zipfiles for all the apps.

    Args:
        all_paths (list): list of ``App`` objects

    Raises:
        IScriptError: on failure

    """
    futures = []
    required_attrs = ["parent_dir", path_attr]
    # zip up apps
    for app in all_paths:
        app.check_required_attrs(required_attrs)
        parent_base_name = os.path.basename(app.parent_dir)
        cwd = os.path.dirname(getattr(app, path_attr))
        path = os.path.basename(getattr(app, path_attr))
        app.zip_path = f"{app.parent_dir}-{path_attr}{parent_base_name}.zip"
        # ditto -c -k --norsrc --keepParent "${BUNDLE}" ${OUTPUT_ZIP_FILE}
        futures.append(
            asyncio.ensure_future(
                run_command(
                    ["zip", "-r", app.zip_path, path], cwd=cwd, exception=IScriptError
                )
            )
        )
    await raise_future_exceptions(futures)


# create_one_notarization_zipfile {{{1
async def create_one_notarization_zipfile(work_dir, all_paths, path_attr="app_path"):
    """Create a single notarization zipfile for all the apps.

    Args:
        work_dir (str): the script work directory
        all_paths (list): list of ``App`` objects
        path_attr (str, optional): the attribute for the paths we'll be zipping
            up. Defaults to ``app_path``

    Raises:
        IScriptError: on failure

    Returns:
        str: the zip path

    """
    required_attrs = [path_attr]
    app_paths = []
    zip_path = os.path.join(work_dir, "{}.zip".format(path_attr))
    for app in all_paths:
        app.check_required_attrs(required_attrs)
        app_paths.append(os.path.relpath(getattr(app, path_attr), work_dir))
    await run_command(
        ["zip", "-r", zip_path, *app_paths], cwd=work_dir, exception=IScriptError
    )
    return zip_path


# sign_all_apps {{{1
async def sign_all_apps(config, key_config, entitlements_path, all_paths):
    """Sign all the apps.

    Args:
        config (dict): the running config
        key_config (dict): the config for this signing key
        entitlements_path (str): the path to the entitlements file, used
            for signing
        all_paths (list): the list of ``App`` objects

    Raises:
        IScriptError: on failure

    """
    log.info("Signing all apps")
    for app in all_paths:
        set_app_path_and_name(app)
    # sign omni.ja
    futures = []
    for app in all_paths:
        if {"autograph_omnija", "omnija"} & set(app.formats):
            futures.append(
                asyncio.ensure_future(
                    sign_omnija_with_autograph(config, key_config, app.app_path)
                )
            )
    await raise_future_exceptions(futures)
    # sign widevine
    futures = []
    for app in all_paths:
        if {"autograph_widevine", "widevine"} & set(app.formats):
            futures.append(
                asyncio.ensure_future(
                    sign_widevine_dir(config, key_config, app.app_path)
                )
            )
    await raise_future_exceptions(futures)
    await unlock_keychain(
        key_config["signing_keychain"], key_config["keychain_password"]
    )
    futures = []
    # sign apps concurrently
    for app in all_paths:
        futures.append(
            asyncio.ensure_future(sign_app(key_config, app.app_path, entitlements_path))
        )
    await raise_future_exceptions(futures)
    # verify signatures
    futures = []
    for app in all_paths:
        futures.append(asyncio.ensure_future(verify_app_signature(key_config, app)))
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
    bundle_id = "{}.{}.{}".format(base_bundle_id, now.timestamp, now.microsecond)
    if counter:
        bundle_id = "{}.{}".format(bundle_id, str(counter))
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
    regex = re.compile(r"RequestUUID = (?P<uuid>[a-zA-Z0-9-]+)")
    try:
        with open(log_path, "r") as fh:
            for line in fh.readlines():
                m = regex.search(line)
                if m:
                    return m["uuid"]
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
    regex = re.compile(r"Status: (?P<status>success|invalid)")
    try:
        with open(log_path, "r") as fh:
            contents = fh.read()
        m = regex.search(contents)
        if m is not None:
            return m["status"]
    except OSError:
        pass


# wrap_notarization_with_sudo {{{1
async def wrap_notarization_with_sudo(
    config, key_config, all_paths, path_attr="zip_path"
):
    """Wrap the notarization requests with sudo.

    Apple creates a lockfile per user for notarization. To notarize concurrently,
    we use sudo against a set of accounts (``config['local_notarization_accounts']``).

    Args:
        config (dict): the running config
        key_config (dict): the config for this signing key
        all_paths (list): the list of ``App`` objects
        path_attr (str, optional): the attribute that the zip path is under.
            Defaults to ``zip_path``

    Raises:
        IScriptError: on failure

    Returns:
        dict: uuid to log path

    """
    futures = []
    accounts = config["local_notarization_accounts"]
    counter = 0
    uuids = {}

    for app in all_paths:
        app.check_required_attrs([path_attr, "parent_dir"])

    while counter < len(all_paths):
        futures = []
        for account in accounts:
            app = all_paths[counter]
            app.notarization_log_path = f"{app.parent_dir}-notarization.log"
            bundle_id = get_bundle_id(
                key_config["base_bundle_id"], counter=str(counter)
            )
            zip_path = getattr(app, path_attr)
            base_cmdln = " ".join(
                [
                    "xcrun",
                    "altool",
                    "--notarize-app",
                    "-f",
                    zip_path,
                    "--primary-bundle-id",
                    '"{}"'.format(bundle_id),
                    "-u",
                    key_config["apple_notarization_account"],
                    "--asc-provider",
                    key_config["apple_asc_provider"],
                    "--password",
                ]
            )
            cmd = [
                "sudo",
                "su",
                account,
                "-c",
                base_cmdln
                + " {}".format(shlex.quote(key_config["apple_notarization_password"])),
            ]
            log_cmd = ["sudo", "su", account, "-c", base_cmdln + " ********"]
            futures.append(
                asyncio.ensure_future(
                    retry_async(
                        run_command,
                        args=[cmd],
                        kwargs={
                            "log_path": app.notarization_log_path,
                            "log_cmd": log_cmd,
                            "exception": IScriptError,
                        },
                        retry_exceptions=(IScriptError,),
                        attempts=10,
                    )
                )
            )
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
    notarization_log_path = os.path.join(work_dir, "notarization.log")
    bundle_id = get_bundle_id(key_config["base_bundle_id"])
    base_cmd = [
        "xcrun",
        "altool",
        "--notarize-app",
        "-f",
        zip_path,
        "--primary-bundle-id",
        bundle_id,
        "-u",
        key_config["apple_notarization_account"],
        "--asc-provider",
        key_config["apple_asc_provider"],
        "--password",
    ]
    log_cmd = base_cmd + ["********"]
    await retry_async(
        run_command,
        args=[base_cmd + [key_config["apple_notarization_password"]]],
        kwargs={
            "log_path": notarization_log_path,
            "log_cmd": log_cmd,
            "exception": IScriptError,
        },
    )
    uuids = {get_uuid_from_log(notarization_log_path): notarization_log_path}
    return uuids


# poll_notarization_uuid {{{1
async def poll_notarization_uuid(
    uuid, username, password, timeout, log_path, sleep_time=15
):
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
    base_cmd = [
        "xcrun",
        "altool",
        "--notarization-info",
        uuid,
        "-u",
        username,
        "--password",
    ]
    log_cmd = base_cmd + ["********"]
    while 1:
        await retry_async(
            run_command,
            args=[base_cmd + [password]],
            kwargs={
                "log_path": log_path,
                "log_cmd": log_cmd,
                "exception": IScriptError,
            },
            retry_exceptions=(IScriptError,),
            attempts=10,
        )
        status = get_notarization_status_from_log(log_path)
        if status == "success":
            break
        if status == "invalid":
            raise InvalidNotarization("Invalid notarization for uuid {}!".format(uuid))
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
        futures.append(
            asyncio.ensure_future(
                poll_notarization_uuid(
                    uuid,
                    key_config["apple_notarization_account"],
                    key_config["apple_notarization_password"],
                    key_config["notarization_poll_timeout"],
                    log_path,
                    sleep_time=15,
                )
            )
        )
    await raise_future_exceptions(futures)


# staple_notarization {{{1
async def staple_notarization(all_paths, path_attr="app_path"):
    """Staple the notarization results to each app.

    Args:
        all_paths (list): the list of App objects
        path_attr (str, optional): the path attribute to staple. Defaults to
            ``app_path``

    Raises:
        IScriptError: on failure

    """
    log.info("Stapling apps")
    futures = []
    for app in all_paths:
        app.check_required_attrs([path_attr, "parent_dir"])
        cwd = os.path.dirname(getattr(app, path_attr))
        path = os.path.basename(getattr(app, path_attr))
        futures.append(
            asyncio.ensure_future(
                retry_async(
                    run_command,
                    args=[["xcrun", "stapler", "staple", "-v", path]],
                    kwargs={
                        "cwd": cwd,
                        "exception": IScriptError,
                        "log_level": logging.DEBUG,
                    },
                    retry_exceptions=(IScriptError,),
                    attempts=10,
                )
            )
        )
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
        app.check_required_attrs(
            ["orig_path", "parent_dir", "app_path", "artifact_prefix"]
        )
        # If we downloaded public/build/locale/target.tar.gz, then write to
        # artifact_dir/public/build/locale/target.tar.gz
        app.target_tar_path = "{}/{}{}".format(
            config["artifact_dir"],
            app.artifact_prefix,
            app.orig_path.split(app.artifact_prefix)[1],
        ).replace(".dmg", ".tar.gz")
        makedirs(os.path.dirname(app.target_tar_path))
        cwd = os.path.dirname(app.app_path)
        env = deepcopy(os.environ)
        # https://superuser.com/questions/61185/why-do-i-get-files-like-foo-in-my-tarball-on-os-x
        env["COPYFILE_DISABLE"] = "1"
        futures.append(
            asyncio.ensure_future(
                run_command(
                    [
                        "tar",
                        _get_tar_create_options(app.target_tar_path),
                        app.target_tar_path,
                    ]
                    + [f for f in os.listdir(cwd) if f != "[]"],
                    cwd=cwd,
                    env=env,
                    exception=IScriptError,
                )
            )
        )
    await raise_future_exceptions(futures)


# create_pkg_files {{{1
async def create_pkg_files(config, key_config, all_paths):
    """Create .pkg installers from the .app files.

    Args:
        key_config (dict): the running config for this key
        all_paths: (list): the list of App objects to pkg

    Raises:
        IScriptError: on failure

    """
    log.info("Creating PKG files")
    futures = []
    semaphore = asyncio.Semaphore(config.get("concurrency_limit", 2))
    for app in all_paths:
        # call set_app_path_and_name because we may not have called sign_app() earlier
        set_app_path_and_name(app)
        app.pkg_path = app.app_path.replace(".app", ".pkg")
        app.pkg_name = os.path.basename(app.pkg_path)
        pkg_opts = []
        if key_config.get("pkg_cert_id"):
            pkg_opts = ["--sign", key_config["pkg_cert_id"]]
        futures.append(
            asyncio.ensure_future(
                semaphore_wrapper(
                    semaphore,
                    run_command(
                        [
                            "sudo",
                            "pkgbuild",
                            "--keychain",
                            key_config["signing_keychain"],
                            "--install-location",
                            "/Applications",
                            "--component",
                            app.app_path,
                            app.pkg_path,
                        ]
                        + pkg_opts,
                        cwd=app.parent_dir,
                        exception=IScriptError,
                    ),
                )
            )
        )
    await raise_future_exceptions(futures)


# copy_pkgs_to_artifact_dir {{{1
async def copy_pkgs_to_artifact_dir(config, all_paths):
    """Copy the files to the artifact directory.

    Args:
        config (dict): the running config
        all_paths (list): the list of App objects to sign pkg for

    """
    log.info("Copying pkgs to the artifact dir")
    for app in all_paths:
        app.check_required_attrs(["orig_path", "pkg_path", "artifact_prefix"])
        app.target_pkg_path = _get_pkg_name_from_tarball(
            "{}/{}{}".format(
                config["artifact_dir"],
                app.artifact_prefix,
                app.orig_path.split(app.artifact_prefix)[1],
            )
        )
        makedirs(os.path.dirname(app.target_pkg_path))
        log.debug("Copying %s to %s", app.pkg_path, app.target_pkg_path)
        copy2(app.pkg_path, app.target_pkg_path)


# download_entitlements_file {{{1
async def download_entitlements_file(config, key_config, task):
    """Download the entitlements file into the work dir.

    Args:
        config (dict): the running configuration
        task (dict): the running task

    Returns:
        str: the path to the downloaded entitlments file
        None: if not ``key_config["sign_with_entitlements"]``

    Raises:
        KeyError: if the plist doesn't include ``CFBundleIdentifier``

    """
    if not key_config["sign_with_entitlements"]:
        return
    url = task["payload"]["entitlements-url"]
    to = os.path.join(config["work_dir"], "browser.entitlements.txt")
    await retry_async(
        download_file, retry_exceptions=(DownloadError, TimeoutError), args=(url, to)
    )
    return to


# notarize_behavior {{{1
async def notarize_behavior(config, task):
    """Sign and notarize all mac apps for this task.

    Args:
        config (dict): the running configuration
        task (dict): the running task

    Raises:
        IScriptError: on fatal error.

    """
    work_dir = config["work_dir"]

    key_config = get_key_config(config, task, base_key="mac_config")
    entitlements_path = await download_entitlements_file(config, key_config, task)

    all_paths = get_app_paths(config, task)
    await extract_all_apps(config, all_paths)
    await unlock_keychain(
        key_config["signing_keychain"], key_config["keychain_password"]
    )
    await update_keychain_search_path(config, key_config["signing_keychain"])
    await sign_all_apps(config, key_config, entitlements_path, all_paths)

    log.info("Notarizing")
    if key_config["notarize_type"] == "multi_account":
        await create_all_notarization_zipfiles(all_paths, path_attr="app_path")
        poll_uuids = await wrap_notarization_with_sudo(
            config, key_config, all_paths, path_attr="zip_path"
        )
    else:
        zip_path = await create_one_notarization_zipfile(
            work_dir, all_paths, path_attr="app_path"
        )
        poll_uuids = await notarize_no_sudo(work_dir, key_config, zip_path)

    await poll_all_notarization_status(key_config, poll_uuids)
    await staple_notarization(all_paths, path_attr="app_path")
    await tar_apps(config, all_paths)

    # pkg
    # Unlock keychain again in case it's locked since previous unlock
    await unlock_keychain(
        key_config["signing_keychain"], key_config["keychain_password"]
    )
    await update_keychain_search_path(config, key_config["signing_keychain"])
    await create_pkg_files(config, key_config, all_paths)
    await copy_pkgs_to_artifact_dir(config, all_paths)

    log.info("Done signing and notarizing apps.")


# sign_behavior {{{1
async def sign_behavior(config, task):
    """Sign all mac apps for this task.

    Args:
        config (dict): the running configuration
        task (dict): the running task

    Raises:
        IScriptError: on fatal error.

    """
    key_config = get_key_config(config, task, base_key="mac_config")
    entitlements_path = await download_entitlements_file(config, key_config, task)

    all_paths = get_app_paths(config, task)
    await extract_all_apps(config, all_paths)
    await unlock_keychain(
        key_config["signing_keychain"], key_config["keychain_password"]
    )
    await update_keychain_search_path(config, key_config["signing_keychain"])
    await sign_all_apps(config, key_config, entitlements_path, all_paths)
    await tar_apps(config, all_paths)
    log.info("Done signing apps.")


# sign_and_pkg {{{1
async def sign_and_pkg_behavior(config, task):
    """Sign all mac apps for this task.

    Args:
        config (dict): the running configuration
        task (dict): the running task

    Raises:
        IScriptError: on fatal error.

    """
    key_config = get_key_config(config, task, base_key="mac_config")
    entitlements_path = await download_entitlements_file(config, key_config, task)

    all_paths = get_app_paths(config, task)
    await extract_all_apps(config, all_paths)
    await unlock_keychain(
        key_config["signing_keychain"], key_config["keychain_password"]
    )
    await update_keychain_search_path(config, key_config["signing_keychain"])
    await sign_all_apps(config, key_config, entitlements_path, all_paths)
    await tar_apps(config, all_paths)

    # pkg
    await unlock_keychain(
        key_config["signing_keychain"], key_config["keychain_password"]
    )
    await update_keychain_search_path(config, key_config["signing_keychain"])
    await create_pkg_files(config, key_config, all_paths)
    await copy_pkgs_to_artifact_dir(config, all_paths)

    log.info("Done signing apps and creating pkgs.")


# sign_geckodriver {{{1
async def geckodriver_behavior(config, task):
    """Create and sign the geckodriver file for this task.

    Args:
        config (dict): the running configuration
        task (dict): the running task

    Raises:
        IScriptError: on fatal error.

    """
    key_config = get_key_config(config, task, base_key="mac_config")

    all_paths = get_app_paths(config, task)
    await extract_all_apps(config, all_paths)
    await unlock_keychain(
        key_config["signing_keychain"], key_config["keychain_password"]
    )
    await update_keychain_search_path(config, key_config["signing_keychain"])
    await sign_geckodriver(config, key_config, all_paths)

    log.info("Done signing geckodriver.")
