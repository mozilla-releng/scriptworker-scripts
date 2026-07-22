#!/usr/bin/env python
"""iscript mac signing functions."""

import asyncio
import logging
import os
import plistlib
from copy import deepcopy
from glob import glob
from shutil import copy2

import attr
import pexpect
from scriptworker_client.aio import download_file, raise_future_exceptions, retry_async, semaphore_wrapper
from scriptworker_client.exceptions import DownloadError
from scriptworker_client.utils import get_artifact_path, makedirs, rm, run_command

from iscript.autograph import sign_langpacks, sign_omnija_with_autograph, sign_widevine_dir
from iscript.exceptions import IScriptError, TimeoutError, UnknownAppDir
from iscript.util import expand_globs, get_sign_config

log = logging.getLogger(__name__)


KNOWN_ARTIFACT_PREFIXES = ("public/", "releng/partner/", "private/openh264/", "project/enterprise/repacks/")


# App {{{1
@attr.s
class App(object):
    """Track the various paths related to each app.

    Attributes:
        orig_path (str): the original path of the app tarball.
        parent_dir (str): the directory that contains the .app.
        app_path (str): the path to the .app directory.
        app_name (str): the basename of the .app directory.
        pkg_path (str): the unsigned .pkg path.
        pkg_name (str): the basename of the .pkg path.
        single_file_globs (list): the globs to sign in the mac_single_file behavior.
        target_bundle_path (str): the path inside of ``artifact_dir`` for the signed
            tarball or zip.
        target_pkg_path (str): the path inside of ``artifact_dir`` for the signed
            .pkg.
        formats (list): the list of formats to sign with.

    """

    orig_path = attr.ib(default="")
    parent_dir = attr.ib(default="")
    app_path = attr.ib(default="")
    app_name = attr.ib(default="")
    pkg_path = attr.ib(default="")
    pkg_name = attr.ib(default="")
    single_file_globs = attr.ib(default="")
    target_bundle_path = attr.ib(default="")
    target_pkg_path = attr.ib(default="")
    formats = attr.ib(default="")
    upstream_task_id = attr.ib(default="")
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


def _retry_run_cmd_semaphore(semaphore, cmd, cwd, exception=IScriptError):
    return asyncio.ensure_future(
        semaphore_wrapper(
            semaphore,
            retry_async(
                func=run_command,
                kwargs={
                    "cmd": cmd,
                    "cwd": cwd,
                    "exception": exception,
                },
                retry_exceptions=(exception,),
            ),
        )
    )


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
    for ext in (".tar.gz", ".tar.bz2", ".dmg", ".pkg"):
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
    with open(os.path.join(appdir, "Contents", "Info.plist"), "rb") as fp:
        return plistlib.load(fp)["CFBundleExecutable"]


# _get_sign_command {{{1
def _get_sign_command(identity, keychain, sign_config, file_=None, entitlements_path=None):
    sign_command = [
        "codesign",
        "-s",
        identity,
        "-fv",
        "--keychain",
        keychain,
        "--requirement",
        sign_config["designated_requirements"] % {"subject_ou": identity},
    ]

    if file_ and file_ in sign_config.get("hardened_runtime_only_files", []):
        sign_command.extend(["-o", "runtime"])
    elif sign_config.get("sign_with_entitlements", False) and entitlements_path:
        sign_command.extend(["-o", "runtime", "--entitlements", entitlements_path])

    return sign_command


# sign_single_files {{{1
async def sign_single_files(config, sign_config, all_paths):
    """Sign a single file.

    Args:
        sign_config (dict): the running config
        all_paths (list): list of App objects

    Raises:
        IScriptError: on error.

    """
    identity = sign_config["identity"]
    keychain = sign_config["signing_keychain"]

    for app in all_paths:
        app.check_required_attrs(["orig_path", "parent_dir", "artifact_prefix", "single_file_globs"])
        app.target_bundle_path = "{}/{}{}".format(config["artifact_dir"], app.artifact_prefix, app.orig_path.split(app.artifact_prefix)[1])
        app.single_paths = expand_globs(app.single_file_globs, parent_dir=app.parent_dir)
        if not app.single_paths:
            raise IScriptError(f"Unable to find anything to sign for {app.orig_path}!")

    for app in all_paths:
        for path in app.single_paths:
            abspath = os.path.join(app.parent_dir, path)
            if not os.path.exists(abspath):
                raise IScriptError(f"No such file {abspath}!")
            sign_command = _get_sign_command(identity, keychain, sign_config, file_=path)
            await retry_async(
                run_command,
                args=[sign_command + [path]],
                kwargs={"cwd": app.parent_dir, "exception": IScriptError, "output_log_on_exception": True},
                retry_exceptions=(IScriptError,),
            )
        env = deepcopy(os.environ)
        makedirs(os.path.dirname(app.target_bundle_path))
        if app.target_bundle_path.endswith(".zip"):
            # Copy the original file to the artifacts dir before adding the
            # signed files to it. This is an openh264 requirement (bug 1689232)
            copy2(app.orig_path, app.target_bundle_path)
            await run_command(
                ["zip", "-f", app.target_bundle_path] + app.single_paths,
                cwd=app.parent_dir,
                env=env,
                exception=IScriptError,
            )
        else:
            # Create a new tarball with just the signed files.
            # https://superuser.com/questions/61185/why-do-i-get-files-like-foo-in-my-tarball-on-os-x
            env["COPYFILE_DISABLE"] = "1"
            await run_command(
                ["tar", _get_tar_create_options(app.target_bundle_path), app.target_bundle_path] + app.single_paths,
                cwd=app.parent_dir,
                env=env,
                exception=IScriptError,
            )


async def _do_sign_file(top_dir, abs_file, file_, sign_command, app_path_len, app_executable):
    # Deal with inner .app's in sign_app, not here.
    if top_dir[app_path_len:].count(".app") > 0:
        log.debug("Skipping %s because it's part of an inner app.", abs_file)
        return
    # app_executable gets signed with the outer package.
    if file_ == app_executable:
        log.debug("Skipping %s because it's the main executable.", abs_file)
        return
    dir_ = os.path.dirname(abs_file)
    await retry_async(
        run_command,
        args=[sign_command + [file_]],
        kwargs={"cwd": dir_, "exception": IScriptError, "output_log_on_exception": True},
        retry_exceptions=(IScriptError,),
    )


# sign_app {{{1
async def sign_app(sign_config, app_path, entitlements_path, provisioning_profile_path=None):
    """Sign the .app.

    Largely taken from build-tools' ``dmg_signfile``.

    Args:
        sign_config (dict): the running config
        app_path (str): the path to the app to be signed (extracted)
        entitlements_path (str): the path to the entitlements file for signing
        provisioning_profile_path (str): the path to a provisioning profile to insert
                                         into the build prior to signing

    Raises:
        IScriptError: on error.

    """
    parent_dir = os.path.dirname(app_path)
    app_name = os.path.basename(app_path)
    await run_command(["xattr", "-cr", app_name], cwd=parent_dir, exception=IScriptError)
    identity = sign_config["identity"]
    keychain = sign_config["signing_keychain"]
    log.debug(f"sign_app: signing {app_name}")

    app_executable = get_bundle_executable(app_path)
    app_path_len = len(app_path)
    contents_dir = os.path.join(app_path, "Contents")

    if provisioning_profile_path:
        log.debug("inserting provisioning profile into app")
        copy2(provisioning_profile_path, os.path.join(contents_dir, "embedded.provisionprofile"))

    for top_dir, dirs, files in os.walk(contents_dir):
        for dir_ in dirs:
            abs_dir = os.path.join(top_dir, dir_)
            if top_dir == contents_dir and dir_ not in sign_config["sign_dirs"]:
                log.debug(f"Skipping {abs_dir} because it's not in `sign_dirs`.")
                dirs.remove(dir_)
                continue
            if dir_ in sign_config["skip_dirs"]:
                log.debug(f"Skipping {abs_dir} because it's in `skip_dirs`.")
                dirs.remove(dir_)
                continue
            if dir_.endswith((".app", ".appex")):
                await sign_app(sign_config, abs_dir, entitlements_path)
            if dir_.endswith(".framework"):
                # Sign the entire .framework folder
                #  codesign cannot determine if it's a Framework or an app bundle if signing the binary directly
                sign_command = _get_sign_command(identity, keychain, sign_config, file_=dir_, entitlements_path=entitlements_path)
                abs_file = os.path.join(top_dir, dir_)
                await _do_sign_file(top_dir, abs_file, dir_, sign_command, app_path_len, app_executable)
                continue
        if top_dir == contents_dir:
            log.debug("Skipping file iteration in %s because it's the root directory.", top_dir)
            continue

        for file_ in files:
            abs_file = os.path.join(top_dir, file_)
            sign_command = _get_sign_command(identity, keychain, sign_config, file_=file_, entitlements_path=entitlements_path)
            await _do_sign_file(top_dir, abs_file, file_, sign_command, app_path_len, app_executable)

    await sign_libclearkey(contents_dir, _get_sign_command(identity, keychain, sign_config, entitlements_path=entitlements_path), app_path)

    # sign bundle
    sign_command = _get_sign_command(identity, keychain, sign_config, entitlements_path=entitlements_path)
    await retry_async(
        run_command,
        args=[sign_command + [app_name]],
        kwargs={"cwd": parent_dir, "exception": IScriptError, "output_log_on_exception": True},
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
                kwargs={"cwd": dir_, "exception": IScriptError, "output_log_on_exception": True},
                retry_exceptions=(IScriptError,),
            )


# verify_app_signature {{{1
async def verify_app_signature(sign_config, app):
    """Verify the app signature.

    Args:
        sign_config (dict): the config for this signing key
        app (App): the app to verify

    Raises:
        IScriptError: on failure

    """
    if not sign_config.get("verify_mac_signature", True):
        return
    required_attrs = ["parent_dir", "app_path"]
    app.check_required_attrs(required_attrs)
    await run_command(["codesign", "-vvv", "--deep", "--strict", app.app_path], cwd=app.parent_dir, exception=IScriptError)


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
    child = pexpect.spawn("security", ["unlock-keychain", signing_keychain], encoding="utf-8")
    try:
        while True:
            index = await child.expect([pexpect.EOF, r"password to unlock {}: ".format(signing_keychain)], async_=True)
            if index == 0:
                break
            child.sendline(keychain_password)
    except pexpect.exceptions.TIMEOUT as exc:
        raise TimeoutError("Timeout trying to unlock the keychain {}: {}!".format(signing_keychain, exc)) from exc
    child.close()
    if child.exitstatus != 0 or child.signalstatus is not None:
        raise IScriptError("Failed unlocking {}! exit {} signal {}".format(signing_keychain, child.exitstatus, child.signalstatus))


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
            [f"{os.environ['HOME']}/Library/Keychains/login.keychain-db", "/Library/Keychains/System.keychain"],
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
    apps = glob("{}/*.app*".format(parent_dir)) + glob("{}/*/*.app*".format(parent_dir)) + glob("{}/*.systemextension*".format(parent_dir))
    if len(apps) != 1:
        raise UnknownAppDir("Can't find a single .app in {}: {}".format(parent_dir, apps))
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
            formats = upstream_artifact_info["formats"]
            if not formats:
                # Signing resources don't have a signing format
                continue
            orig_path = get_artifact_path(upstream_artifact_info["taskId"], subpath, work_dir=config["work_dir"])

            app = App(
                orig_path=orig_path,
                formats=formats,
                artifact_prefix=_get_artifact_prefix(subpath),
                upstream_task_id=upstream_artifact_info["taskId"],
            )
            if "mac_geckodriver" in formats or "mac_single_file" in formats:
                app.single_file_globs = upstream_artifact_info.get("singleFileGlobs", ["geckodriver"])
            all_paths.append(app)
    return all_paths


def get_langpack_format(app):
    return next((f for f in app.formats if "langpack" in f), None)


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
                        log_level=logging.DEBUG,
                    )
                )
            )
        elif app.orig_path.endswith(".dmg"):
            unpack_mountpoint = os.path.join("/tmp", f"{config.get('dmg_prefix', 'dmg')}-{counter}-unpack")
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
        elif app.orig_path.endswith(".zip"):
            futures.append(asyncio.ensure_future(run_command(["unzip", app.orig_path], cwd=app.parent_dir, exception=IScriptError, log_level=logging.DEBUG)))
        else:
            raise IScriptError(f"unknown file type {app.orig_path}")
    await raise_future_exceptions(futures)
    if app.orig_path.endswith(".dmg"):
        # nuke the softlink to /Applications
        for counter, app in enumerate(all_paths):
            rm(os.path.join(app.parent_dir, " "))


# sign_all_apps {{{1
async def sign_all_apps(config, sign_config, entitlements_path, all_paths, provisioning_profile_path):
    """Sign all the apps.

    Args:
        config (dict): the running config
        sign_config (dict): the config for this signing key
        entitlements_path (str): the path to the entitlements file, used
            for signing
        provisioning_profile_path (str): the path to a provisioning profile to insert
                                         into the build prior to signing
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
        fmt = next((f for f in app.formats if "omnija" in f), None)
        if fmt:
            futures.append(asyncio.ensure_future(sign_omnija_with_autograph(config, sign_config, app.app_path, fmt)))
    await raise_future_exceptions(futures)
    # sign widevine
    futures = []
    for app in all_paths:
        fmt = next((f for f in app.formats if "widevine" in f), None)
        if fmt:
            futures.append(asyncio.ensure_future(sign_widevine_dir(config, sign_config, app.app_path, fmt)))
    await raise_future_exceptions(futures)
    await unlock_keychain(sign_config["signing_keychain"], sign_config["keychain_password"])
    futures = []
    # sign apps concurrently
    for app in all_paths:
        futures.append(asyncio.ensure_future(sign_app(sign_config, app.app_path, entitlements_path, provisioning_profile_path)))
    await raise_future_exceptions(futures)
    # verify signatures
    futures = []
    for app in all_paths:
        futures.append(asyncio.ensure_future(verify_app_signature(sign_config, app)))
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
        app.check_required_attrs(["orig_path", "parent_dir", "app_path", "artifact_prefix"])
        # If we downloaded public/build/locale/target.tar.gz, then write to
        # artifact_dir/public/build/locale/target.tar.gz
        app.target_bundle_path = "{}/{}{}".format(config["artifact_dir"], app.artifact_prefix, app.orig_path.split(app.artifact_prefix)[1]).replace(
            ".dmg", ".tar.gz"
        )
        makedirs(os.path.dirname(app.target_bundle_path))
        cwd = os.path.dirname(app.app_path)
        env = deepcopy(os.environ)
        # https://superuser.com/questions/61185/why-do-i-get-files-like-foo-in-my-tarball-on-os-x
        env["COPYFILE_DISABLE"] = "1"
        futures.append(
            asyncio.ensure_future(
                run_command(
                    ["tar", _get_tar_create_options(app.target_bundle_path), app.target_bundle_path]
                    + [f for f in os.listdir(cwd) if f != "[]" and not f.endswith(".pkg")],
                    cwd=cwd,
                    env=env,
                    exception=IScriptError,
                )
            )
        )
    await raise_future_exceptions(futures)


# create_pkg_files {{{1
async def create_pkg_files(config, sign_config, all_paths, requirements_plist_path=None):
    """Create .pkg installers from the .app files.

    Args:
        sign_config (dict): the running config for this key
        all_paths (list): the list of App objects to pkg
        requirements_plist_path (str): Path to a ``requirements.plist`` file
            to pass into productbuild (optional)

    Raises:
        IScriptError: on failure

    """
    log.info("Creating PKG files")
    futures = []
    semaphore = asyncio.Semaphore(config.get("concurrency_limit", 2))
    cmd_opts = []
    if sign_config.get("pkg_cert_id"):
        cmd_opts = ["--keychain", sign_config["signing_keychain"], "--sign", sign_config["pkg_cert_id"]]
    for app in all_paths:
        # call set_app_path_and_name because we may not have called sign_app() earlier
        set_app_path_and_name(app)
        app.tmp_pkg_path1 = app.app_path.replace(".appex", ".tmp1.pkg").replace(".app", ".tmp1.pkg")
        app.tmp_pkg_path2 = app.app_path.replace(".appex", ".tmp2.pkg").replace(".app", ".tmp2.pkg")
        app.pkg_path = app.app_path.replace(".appex", ".pkg").replace(".app", ".pkg")
        app.pkg_name = os.path.basename(app.pkg_path)
        cmd = (
            "pkgbuild",
            "--install-location",
            "/Applications",
            *cmd_opts,
            "--component",
            app.app_path,
            app.tmp_pkg_path1,
        )
        futures.append(_retry_run_cmd_semaphore(semaphore=semaphore, cmd=cmd, cwd=app.parent_dir))
    await raise_future_exceptions(futures)
    futures = []
    for app in all_paths:
        pb_opts = []
        if requirements_plist_path:
            pb_opts.extend(["--product", requirements_plist_path])
        pb_opts.extend(
            [
                "--package",
                app.tmp_pkg_path1,
                app.tmp_pkg_path2,
            ]
        )
        # Bug 1689376 - create distribution pkg
        cmd = ("productbuild", *cmd_opts, *pb_opts)
        futures.append(_retry_run_cmd_semaphore(semaphore=semaphore, cmd=cmd, cwd=app.parent_dir))
    await raise_future_exceptions(futures)
    futures = []
    for app in all_paths:
        if sign_config.get("pkg_cert_id"):
            # Bug 1689376 - sign distribution pkg
            cmd = ("productsign", *cmd_opts, app.tmp_pkg_path2, app.pkg_path)
            futures.append(_retry_run_cmd_semaphore(semaphore=semaphore, cmd=cmd, cwd=app.parent_dir))
        else:
            copy2(app.tmp_pkg_path2, app.pkg_path)
    await raise_future_exceptions(futures)


# copy_pkgs_to_artifact_dir {{{1
async def copy_pkgs_to_artifact_dir(config, all_paths):
    """Copy the pkg files to the artifact directory.

    Args:
        config (dict): the running config
        all_paths (list): the list of App objects to sign pkg for

    """
    log.info("Copying pkgs to the artifact dir")
    for app in all_paths:
        app.check_required_attrs(["orig_path", "pkg_path", "artifact_prefix"])
        app.target_pkg_path = _get_pkg_name_from_tarball(
            "{}/{}{}".format(config["artifact_dir"], app.artifact_prefix, app.orig_path.split(app.artifact_prefix)[1])
        )
        makedirs(os.path.dirname(app.target_pkg_path))
        log.debug("Copying %s to %s", app.pkg_path, app.target_pkg_path)
        copy2(app.pkg_path, app.target_pkg_path)


# download_entitlements_file {{{1
async def download_entitlements_file(config, sign_config, task):
    """Download the entitlements file into the work dir.

    Args:
        config (dict): the running configuration
        task (dict): the running task

    Returns:
        str: the path to the downloaded entitlments file
        None: if not ``sign_config["sign_with_entitlements"]``

    """
    if not sign_config["sign_with_entitlements"]:
        return
    url = task["payload"]["entitlements-url"]
    to = os.path.join(config["work_dir"], "browser.entitlements.txt")
    await retry_async(download_file, retry_exceptions=(DownloadError, TimeoutError), args=(url, to))
    return to


# download_provisioning_profile {{{1
async def download_provisioning_profile(config, task):
    """Download the provisioning profile into the work dir.

    Args:
        config (dict): the running configuration
        task (dict): the running task

    Returns:
        str: the path to the downloaded provisioning profile
        None: if not ``payload["provisioning-profile-url"]``

    """
    url = task["payload"].get("provisioning-profile-url")
    if not url:
        return None
    to = os.path.join(config["work_dir"], "provisioning.profile")
    await retry_async(download_file, retry_exceptions=(DownloadError, TimeoutError), args=(url, to))
    return to


# download_requirements_plist_file {{{1
async def download_requirements_plist_file(config, task):
    """Download the entitlements file into the work dir.

    Args:
        config (dict): the running configuration
        task (dict): the running task

    Returns:
        str: the path to the downloaded requirements.plist file
        None: if not ``payload["requirements-plist-url"]``

    """
    url = task["payload"].get("requirements-plist-url")
    if not url:
        return
    to = os.path.join(config["work_dir"], "requirements.plist")
    await retry_async(download_file, retry_exceptions=(DownloadError, TimeoutError), args=(url, to))
    return to


# sign_behavior {{{1
async def sign_behavior(config, task):
    """Sign all mac apps for this task.

    Args:
        config (dict): the running configuration
        task (dict): the running task

    Raises:
        IScriptError: on fatal error.

    """
    sign_config = get_sign_config(config, task, base_key="mac_config")
    entitlements_path = await download_entitlements_file(config, sign_config, task)
    provisioning_profile_path = await download_provisioning_profile(config, task)

    non_langpack_apps = []
    for app in get_app_paths(config, task):
        if fmt := get_langpack_format(app):
            await sign_langpacks(config, sign_config, [app], fmt)
        else:
            non_langpack_apps.append(app)
    await extract_all_apps(config, non_langpack_apps)
    await unlock_keychain(sign_config["signing_keychain"], sign_config["keychain_password"])
    await update_keychain_search_path(config, sign_config["signing_keychain"])
    await sign_all_apps(config, sign_config, entitlements_path, non_langpack_apps, provisioning_profile_path)
    await tar_apps(config, non_langpack_apps)
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
    sign_config = get_sign_config(config, task, base_key="mac_config")
    entitlements_path = await download_entitlements_file(config, sign_config, task)
    provisioning_profile_path = await download_provisioning_profile(config, task)
    requirements_plist_path = await download_requirements_plist_file(config, task)

    non_langpack_apps = []
    for app in get_app_paths(config, task):
        if fmt := get_langpack_format(app):
            await sign_langpacks(config, sign_config, [app], fmt)
        else:
            non_langpack_apps.append(app)
    await extract_all_apps(config, non_langpack_apps)
    await unlock_keychain(sign_config["signing_keychain"], sign_config["keychain_password"])
    await update_keychain_search_path(config, sign_config["signing_keychain"])
    await sign_all_apps(config, sign_config, entitlements_path, non_langpack_apps, provisioning_profile_path)
    await tar_apps(config, non_langpack_apps)

    # pkg
    await unlock_keychain(sign_config["signing_keychain"], sign_config["keychain_password"])
    await update_keychain_search_path(config, sign_config["signing_keychain"])
    await create_pkg_files(config, sign_config, non_langpack_apps, requirements_plist_path=requirements_plist_path)
    await copy_pkgs_to_artifact_dir(config, non_langpack_apps)

    log.info("Done signing apps and creating pkgs.")


# single_file_behavior {{{1
async def single_file_behavior(config, task):
    """Create and sign the single file for this task.

    Args:
        config (dict): the running configuration
        task (dict): the running task

    Raises:
        IScriptError: on fatal error.

    """
    sign_config = get_sign_config(config, task, base_key="mac_config")

    non_langpack_apps = []
    for app in get_app_paths(config, task):
        if fmt := get_langpack_format(app):
            await sign_langpacks(config, sign_config, [app], fmt)
        else:
            non_langpack_apps.append(app)
    await extract_all_apps(config, non_langpack_apps)
    await unlock_keychain(sign_config["signing_keychain"], sign_config["keychain_password"])
    await update_keychain_search_path(config, sign_config["signing_keychain"])
    await sign_single_files(config, sign_config, non_langpack_apps)

    log.info("Done signing single files.")
