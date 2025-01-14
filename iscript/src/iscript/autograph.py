#!/usr/bin/env python
"""Widevine signing functions."""

import asyncio
import base64
import difflib
import glob
import json
import logging
import os
import re
import tempfile
import zipfile

import requests
from mozpack import mozjar
from requests_hawk import HawkAuth

from iscript.constants import LANGPACK_AUTOGRAPH_KEY_ID, OMNIJA_AUTOGRAPH_KEY_ID
from iscript.createprecomplete import generate_precomplete
from iscript.exceptions import IScriptError
from scriptworker_client.aio import raise_future_exceptions, retry_async
from scriptworker_client.utils import makedirs, rm

try:
    # NB. The widevine module needs to be deployed separately
    import widevine
except ImportError:
    widevine = None


log = logging.getLogger(__name__)

# These files load the Widevine CDM and therefore need a .sig file to be
# generated.
_WIDEVINE_BLESSED_FILENAMES = (
    # On macOS, newer versions of Firefox will transition to use the
    # "* Media Plugin Helper" executable instead of plugin-container for
    # Widevine. plugin-container and plugin-container.exe will continue to
    # be used for Linux and Windows respectively.
    "Firefox Media Plugin Helper",
    "Firefox Developer Edition Media Plugin Helper",
    "Firefox Nightly Media Plugin Helper",
    "Nightly Media Plugin Helper",
    "plugin-container",
    "plugin-container.exe",
)
# These are other files that need to be widevine-signed
_WIDEVINE_NONBLESSED_FILENAMES = (
    # firefox
    "firefox",
    "firefox-bin",
    "firefox.exe",
    # xul
    "libxul.so",
    "XUL",
    "xul.dll",
    # clearkey for regression testing.
    "clearkey.dll",
    "libclearkey.dylib",
    "libclearkey.so",
)
# Langpacks expect the following re to match for addon id
LANGPACK_RE = re.compile(r"^langpack-[a-zA-Z]+(?:-[a-zA-Z]+){0,2}@(?:firefox|devedition).mozilla.org$")


# sign_widevine_dir {{{1
async def sign_widevine_dir(config, sign_config, app_dir, autograph_fmt):
    """Sign the internals of a tarfile with the widevine key.

    Extract the entire tarball, but only sign a handful of files (see
    `_WIDEVINE_BLESSED_FILENAMES` and `_WIDEVINE_UNBLESSED_FILENAMES).
    The blessed files should be signed with the `widevine_blessed` format.
    Then recreate the tarball.

    Ideally we would be able to append the sigfiles to the original tarball,
    but that's not possible with compressed tarballs.

    Args:
        config (dict): the running config
        sign_config (dict): the config for this signing key
        app_dir (str): the .app directory to sign

    Returns:
        str: the path to the signed archive

    """
    log.info(f"Signing widevine in {app_dir}...")
    all_files = []
    for top_dir, dirs, files in os.walk(app_dir):
        for file_ in files:
            all_files.append(os.path.join(top_dir, file_))
    files_to_sign = _get_widevine_signing_files(all_files)
    log.debug("Widevine files to sign: %s", files_to_sign)
    if files_to_sign:
        tasks = []
        for from_, fmt in files_to_sign.items():
            to = _get_mac_sigpath(from_)
            log.debug("Adding %s to the sigfile paths...", to)
            makedirs(os.path.dirname(to))
            tasks.append(asyncio.ensure_future(sign_widevine_with_autograph(sign_config, from_, autograph_fmt, "blessed" in fmt, to=to)))
            all_files.append(to)
        await raise_future_exceptions(tasks)
        remove_extra_files(app_dir, all_files)
        # Regenerate the `precomplete` file, which is used for cleanup before
        # applying a complete mar.
        _run_generate_precomplete(config, app_dir)
    return app_dir


# _get_mac_sigpath {{{1
def _get_mac_sigpath(from_):
    """For mac paths, replace the final Contents/MacOS/ with Contents/Resources/."""
    to = from_
    if "Contents/MacOS" in from_:
        parts = from_.split("/")
        parts.reverse()
        i = parts.index("MacOS")
        parts[i] = "Resources"
        parts.reverse()
        to = "/".join(parts)
        log.debug("Sigfile for {} should be {}.sig".format(from_, to))
    return "{}.sig".format(to)


# _get_widevine_signing_files {{{1
def _get_widevine_signing_files(file_list):
    """Return a dict of path:signing_format for each path to be signed."""
    files = {}
    for filename in file_list:
        fmt = None
        base_filename = os.path.basename(filename)
        if base_filename in _WIDEVINE_BLESSED_FILENAMES:
            fmt = "widevine_blessed"
        elif base_filename in _WIDEVINE_NONBLESSED_FILENAMES:
            fmt = "widevine"
        if fmt:
            log.debug("Found {} to sign {}".format(filename, fmt))
            sigpath = _get_mac_sigpath(filename)
            if sigpath not in file_list:
                files[filename] = fmt
            else:
                log.debug("{} is already signed! Skipping...".format(filename))
    return files


# _run_generate_precomplete {{{1
def _run_generate_precomplete(config, app_dir):
    """Regenerate `precomplete` file with widevine sig paths for complete mar."""
    log.info("Generating `precomplete` file...")
    path = _ensure_one_precomplete(app_dir, "before")
    with open(path, "r") as fh:
        before = fh.readlines()
    generate_precomplete(os.path.dirname(path))
    path = _ensure_one_precomplete(app_dir, "after")
    with open(path, "r") as fh:
        after = fh.readlines()
    # Create diff file
    makedirs(os.path.join(config["artifact_dir"], "public", "logs"))
    diff_path = os.path.join(config["artifact_dir"], "public", "logs", "precomplete.diff")
    with open(diff_path, "w") as fh:
        for line in difflib.ndiff(before, after):
            fh.write(line)


# _ensure_one_precomplete {{{1
def _ensure_one_precomplete(tmp_dir, adj):
    """Ensure we only have one `precomplete` file in `tmp_dir`."""
    precompletes = glob.glob(os.path.join(tmp_dir, "**", "precomplete"), recursive=True)
    if len(precompletes) < 1:
        raise IScriptError('No `precomplete` file found in "%s"', tmp_dir)
    if len(precompletes) > 1:
        raise IScriptError('More than one `precomplete` file %s in "%s"', adj, tmp_dir)
    return precompletes[0]


# remove_extra_files {{{1
def remove_extra_files(top_dir, file_list):
    """Find any extra files in `top_dir`, given an expected `file_list`.

    Args:
        top_dir (str): the dir to walk
        file_list (list): the list of expected files

    Returns:
        list: the list of extra files

    """
    all_files = [os.path.realpath(f) for f in glob.glob(os.path.join(top_dir, "**", "*"), recursive=True)]
    good_files = [os.path.realpath(f) for f in file_list]
    extra_files = list(set(all_files) - set(good_files))
    for f in extra_files:
        if os.path.isfile(f):
            log.warning("Extra file to clean up: {}".format(f))
            rm(f)
    return extra_files


# autograph {{{1
async def call_autograph(url, user, password, request_json):
    """Call autograph and return the json response.

    Args:
        url (str): the endpoint url
        user (str): the autograph user
        password (str): the autograph password
        request_json (dict): list of dictionaries, from ``make_signing_req``

    Raises:
        requests.RequestException: on failure

    Returns:
        dict: the response json

    """
    auth = HawkAuth(id=user, key=password)
    with requests.Session() as session:
        r = session.post(url, json=request_json, auth=auth)
        log.debug("Autograph response: %s", r.text[:120] if len(r.text) >= 120 else r.text)
        r.raise_for_status()
        return r.json()


def make_signing_req(input_bytes, fmt, keyid=None, extension_id=None):
    """Make a signing request object to pass to autograph.

    Args:
        input_bytes (bytestring): the hash or filedata to sign
        fmt (string): the format to sign with
        keyid (string, optional): the keyid to use to sign with. If ``None``,
            we use the default keyid configured in autograph. Defaults to ``None``.

    Returns:
        list: the signing request json

    """
    base64_input = base64.b64encode(input_bytes).decode("ascii")
    sign_req = {"input": base64_input}

    if keyid:
        sign_req["keyid"] = keyid

    if "omnija" in fmt or "langpack" in fmt:
        sign_req.setdefault("options", {})
        # https://bugzilla.mozilla.org/show_bug.cgi?id=1533818#c9
        sign_req["options"]["id"] = extension_id
        sign_req["options"]["cose_algorithms"] = ["ES256"]
        sign_req["options"]["pkcs7_digest"] = "SHA256"
        log.debug(f"{fmt} sign_req options: {sign_req['options']}")

    return [sign_req]


async def sign_with_autograph(sign_config, input_bytes, fmt, autograph_method, keyid=None, extension_id=None):
    """Signs data with autograph and returns the result.

    Args:
        sign_config (dict): the running config for this key
        input_bytes (bytes): the source data to sign
        fmt (str): the format to sign with
        autograph_method (str): which autograph method to use to sign. must be
                                one of 'file', 'hash', or 'data'
        keyid (str): which key to use on autograph (optional)
        extension_id (str): which id to send to autograph for the extension (optional)

    Raises:
        Requests.RequestException: on failure

    Returns:
        bytes: the signed data

    """
    if autograph_method not in {"file", "hash", "data"}:
        raise IScriptError(f"Unsupported autograph method: {autograph_method}")

    sign_req = make_signing_req(input_bytes, fmt, keyid=keyid, extension_id=extension_id)
    short_fmt = fmt.replace("autograph_", "")
    url = sign_config[f"{short_fmt}_url"]
    user = sign_config[f"{short_fmt}_user"]
    pw = sign_config[f"{short_fmt}_pass"]

    log.debug("signing data with format %s with %s", fmt, autograph_method)

    url = f"{url}/sign/{autograph_method}"

    sign_resp = await retry_async(call_autograph, args=(url, user, pw, sign_req), attempts=3, sleeptime_kwargs={"delay_factor": 2.0})

    if autograph_method == "file":
        return sign_resp[0]["signed_file"]
    else:
        return sign_resp[0]["signature"]


async def sign_file_with_autograph(sign_config, from_, fmt, to=None, keyid=None, extension_id=None):
    """Signs file with autograph and writes the results to a file.

    Args:
        sign_config (dict): the running config for this key
        from_ (str): the source file to sign
        fmt (str): the format to sign with
        to (str, optional): the target path to sign to. If None, overwrite
                            `from_`. Defaults to None.
        extension_id (str, optional): the extension id to use when signing.

    Raises:
        Requests.RequestException: on failure

    Returns:
        str: the path to the signed file

    """
    to = to or from_
    input_bytes = open(from_, "rb").read()
    signed_bytes = base64.b64decode(
        await sign_with_autograph(
            sign_config,
            input_bytes,
            fmt,
            "file",
            keyid=keyid,
            extension_id=extension_id,
        )
    )
    with open(to, "wb") as fout:
        fout.write(signed_bytes)
    return to


async def sign_hash_with_autograph(sign_config, hash_, fmt, keyid=None):
    """Signs hash with autograph and returns the result.

    Args:
        sign_config (dict): the running config for this key
        hash_ (bytes): the input hash to sign
        fmt (str): the format to sign with
        keyid (str): which key to use on autograph (optional)

    Raises:
        Requests.RequestException: on failure

    Returns:
        bytes: the signature

    """
    signature = base64.b64decode(await sign_with_autograph(sign_config, hash_, fmt, "hash", keyid))
    return signature


# omnija {{{1
def _get_omnija_signing_files(file_list):
    """Return a dict of path:signing_format for each path to be signed."""
    files = {}
    for filename in file_list:
        fmt = None
        base_filename = os.path.basename(filename)
        if base_filename in {"omni.ja"}:
            fmt = "autograph_omnija"
        if fmt:
            log.debug("Found {} to sign {}".format(filename, fmt))
            files[filename] = fmt
    return files


async def sign_omnija_with_autograph(config, sign_config, app_path):
    """Sign the omnija file specified using autograph.

    This function overwrites from_
    rebuild it using the signed meta-data and the original omni.ja
    in order to facilitate the performance wins we do as part of the build

    Args:
        config (dict): the running config
        sign_config (dict): the running config for this key
        app_path (str): the path to the .app dir

    Raises:
        Requests.RequestException: on failure

    Returns:
        str: the path to the signature file

    """
    log.info(f"Signing omnija in {app_path}...")
    all_files = []
    for top_dir, dirs, files in os.walk(app_path):
        for file_ in files:
            all_files.append(os.path.join(top_dir, file_))
    files_to_sign = _get_omnija_signing_files(all_files)
    for from_ in files_to_sign:
        signed_out = tempfile.mkstemp(prefix="oj_signed", suffix=".ja", dir=config["work_dir"])[1]
        merged_out = tempfile.mkstemp(prefix="oj_merged", suffix=".ja", dir=config["work_dir"])[1]

        await sign_file_with_autograph(
            sign_config,
            from_,
            "autograph_omnija",
            to=signed_out,
            keyid=OMNIJA_AUTOGRAPH_KEY_ID[sign_config.get("release_type", "dep")],
            extension_id="omni.ja@mozilla.org",
        )
        await merge_omnija_files(orig=from_, signed=signed_out, to=merged_out)
        with open(from_, "wb") as fout:
            with open(merged_out, "rb") as fin:
                fout.write(fin.read())
    return files_to_sign


async def merge_omnija_files(orig, signed, to):
    """Merge multiple omnijar files together.

    This takes the original file, and reads it in, including performance
    characteristics (e.g. jarlog ordering for preloading),
    then adds data from the "signed" copy (the META-INF folder)
    and finally writes it all out to a new omni.ja file.

    Args:
        orig (str): the source file to sign
        signed (str): the signed file, without optimizations
        to (str): the output path for the merge

    Returns:
        bool: always True if function succeeded.

    """
    orig_jarreader = mozjar.JarReader(orig)
    with mozjar.JarWriter(to, compress=orig_jarreader.compression) as to_writer:
        for origjarfile in orig_jarreader:
            to_writer.add(origjarfile.filename, origjarfile, compress=origjarfile.compress)
        # Use ZipFile here because mozjar can't read the signed copies
        signed_zip = zipfile.ZipFile(signed, "r")
        for fname in signed_zip.namelist():
            if fname.startswith("META-INF"):
                to_writer.add(fname, signed_zip.open(fname, "r"))
        if orig_jarreader.last_preloaded:
            jarlog = list(orig_jarreader.entries.keys())
            preloads = jarlog[: jarlog.index(orig_jarreader.last_preloaded) + 1]
            to_writer.preload(preloads)
    return True


# sign_widevine_with_autograph {{{1
async def sign_widevine_with_autograph(sign_config, from_, fmt, blessed, to=None):
    """Create a widevine signature using autograph as a backend.

    Args:
        sign_config (dict): the running config for this key
        from_ (str): the source file to sign
        fmt (str): the format to sign with
        blessed (bool): whether to use blessed signing or not
        to (str, optional): the target path to sign to. If None, write to
            `{from_}.sig`. Defaults to None.

    Raises:
        Requests.RequestException: on failure

    Returns:
        str: the path to the signature file

    """
    if not widevine:
        raise ImportError("widevine module not available")

    to = to or f"{from_}.sig"
    flags = 1 if blessed else 0

    h = widevine.generate_widevine_hash(from_, flags)

    signature = await sign_hash_with_autograph(sign_config, h, fmt)

    with open(to, "wb") as fout:
        certificate = open(sign_config["widevine_cert"], "rb").read()
        sig = widevine.generate_widevine_signature(signature, certificate, flags)
        fout.write(sig)
    return to


def langpack_id(app):
    """Return a list of id's for the langpacks.

    Side effect of checking if filenames are actually langpacks.
    """
    _, file_extension = os.path.splitext(app.orig_path)
    if not file_extension == ".xpi":
        raise IScriptError(f"Expected an xpi got {app.orig_path}")

    langpack = zipfile.ZipFile(app.orig_path, "r")
    id = None
    with langpack.open("manifest.json", "r") as f:
        manifest = json.load(f)
        browser_specific_settings = manifest.get("browser_specific_settings", manifest.get("applications", {}))
        if not (
            "languages" in manifest
            and "langpack_id" in manifest
            and "gecko" in browser_specific_settings
            and "id" in browser_specific_settings["gecko"]
            and LANGPACK_RE.match(browser_specific_settings["gecko"]["id"])
        ):
            raise IScriptError(f"{app.orig_path} is not a valid langpack")
        id = browser_specific_settings["gecko"]["id"]
    return id


async def sign_langpacks(config, sign_config, all_paths):
    """Signs langpacks that are specified in all_paths.

    Raises:
        IScriptError if we don't have any valid language packs to sign in any path.

    """
    for app in all_paths:
        app.check_required_attrs(["orig_path", "formats", "artifact_prefix"])
        if not {"autograph_langpack"} & set(app.formats):
            raise IScriptError(f"{app.formats} does not contain 'autograph_langpack'")
        app.target_bundle_path = "{}/{}{}".format(config["artifact_dir"], app.artifact_prefix, app.orig_path.split(app.artifact_prefix)[1])

        id = langpack_id(app)
        log.info("Identified {} as extension id: {}".format(app.orig_path, id))
        makedirs(os.path.dirname(app.target_bundle_path))
        await sign_file_with_autograph(
            sign_config,
            app.orig_path,
            "autograph_langpack",
            to=app.target_bundle_path,
            keyid=LANGPACK_AUTOGRAPH_KEY_ID[sign_config.get("release_type", "dep")],
            extension_id=id,
        )
