#!/usr/bin/env python
"""Widevine signing functions."""
import asyncio
import base64
import difflib
import glob
import logging
import os
import requests
import tempfile

from iscript.createprecomplete import generate_precomplete
from iscript.exceptions import IScriptError
from requests_hawk import HawkAuth
from scriptworker_client.aio import raise_future_exceptions, retry_async
from scriptworker_client.utils import makedirs, rm

try:
    # NB. The widevine module needs to be deployed separately
    import widevine
except ImportError:
    widevine = None


log = logging.getLogger(__name__)

# Blessed files call the other widevine files.
_WIDEVINE_BLESSED_FILENAMES = (
    # plugin-container is the top of the calling stack
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


# sign_widevine_tar {{{1
async def sign_widevine_tar(config, key_config, orig_path, fmt):
    """Sign the internals of a tarfile with the widevine key.

    Extract the entire tarball, but only sign a handful of files (see
    `_WIDEVINE_BLESSED_FILENAMES` and `_WIDEVINE_UNBLESSED_FILENAMES).
    The blessed files should be signed with the `widevine_blessed` format.
    Then recreate the tarball.

    Ideally we would be able to append the sigfiles to the original tarball,
    but that's not possible with compressed tarballs.

    Args:
        config (dict): the running config
        key_config (dict): the config for this signing key
        orig_path (str): the source file to sign
        fmt (str): the format to sign with

    Returns:
        str: the path to the signed archive

    """
    _, compression = os.path.splitext(orig_path)
    # This will get cleaned up when we nuke `work_dir`. Clean up at that point
    # rather than immediately after `sign_widevine`, to optimize task runtime
    # speed over disk space.
    tmp_dir = tempfile.mkdtemp(prefix="wvtar", dir=config["work_dir"])
    # Get file list
    # TODO look at the extracted dir
    all_files = []  # await _get_tarfile_files(orig_path, compression)
    files_to_sign = _get_widevine_signing_files(all_files)
    log.debug("Widevine files to sign: %s", files_to_sign)
    if files_to_sign:
        # TODO walk the already extracted dir
        tasks = []
        # Sign the appropriate inner files
        for from_, fmt in files_to_sign.items():
            from_ = os.path.join(tmp_dir, from_)
            # Don't try to sign directories
            if not os.path.isfile(from_):
                continue
            # Move the sig location on mac. This should be noop on linux.
            to = _get_mac_sigpath(from_)
            log.debug("Adding %s to the sigfile paths...", to)
            makedirs(os.path.dirname(to))
            tasks.append(
                asyncio.ensure_future(
                    sign_widevine_with_autograph(
                        key_config, from_, "blessed" in fmt, to=to
                    )
                )
            )
            all_files.append(to)
        await raise_future_exceptions(tasks)
        remove_extra_files(tmp_dir, all_files)
        # Regenerate the `precomplete` file, which is used for cleanup before
        # applying a complete mar.
        _run_generate_precomplete(config, tmp_dir)
        # XXX
        # await _create_tarfile(
        #    context, orig_path, all_files, compression, tmp_dir=tmp_dir
        # )
    return orig_path


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
def _run_generate_precomplete(config, tmp_dir):
    """Regenerate `precomplete` file with widevine sig paths for complete mar."""
    log.info("Generating `precomplete` file...")
    path = _ensure_one_precomplete(tmp_dir, "before")
    with open(path, "r") as fh:
        before = fh.readlines()
    generate_precomplete(os.path.dirname(path))
    path = _ensure_one_precomplete(tmp_dir, "after")
    with open(path, "r") as fh:
        after = fh.readlines()
    # Create diff file
    diff_path = os.path.join(config["work_dir"], "precomplete.diff")
    with open(diff_path, "w") as fh:
        for line in difflib.ndiff(before, after):
            fh.write(line)
    # XXX
    # utils.copy_to_dir(
    #    diff_path, config["artifact_dir"], target="public/logs/precomplete.diff"
    # )


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
    all_files = [
        os.path.realpath(f)
        for f in glob.glob(os.path.join(top_dir, "**", "*"), recursive=True)
    ]
    good_files = [os.path.realpath(f) for f in file_list]
    extra_files = list(set(all_files) - set(good_files))
    for f in extra_files:
        if os.path.isfile(f):
            log.warning("Extra file to clean up: {}".format(f))
            rm(f)
    return extra_files


# autograph {{{1
async def call_autograph(url, user, password, request_json):
    """Call autograph and return the json response."""
    auth = HawkAuth(id=user, key=password)
    with requests.Session() as session:
        r = session.post(url, json=request_json, auth=auth)
        log.debug(
            "Autograph response: %s", r.text[:120] if len(r.text) >= 120 else r.text
        )
        r.raise_for_status()
        return r.json()


def make_signing_req(input_bytes, keyid=None):
    """Make a signing request object to pass to autograph."""
    base64_input = base64.b64encode(input_bytes).decode("ascii")
    sign_req = {"input": base64_input}

    if keyid:
        sign_req["keyid"] = keyid

    return [sign_req]


async def sign_with_autograph(
    key_config, input_bytes, fmt, autograph_method, keyid=None
):
    """Signs data with autograph and returns the result.

    Args:
        key_config (dict): the running config for this key
        input_bytes (bytes): the source data to sign
        fmt (str): the format to sign with
        autograph_method (str): which autograph method to use to sign. must be
                                one of 'file', 'hash', or 'data'
        keyid (str): which key to use on autograph (optional)

    Raises:
        Requests.RequestException: on failure

    Returns:
        bytes: the signed data

    """
    if autograph_method not in {"file", "hash", "data"}:
        raise IScriptError(f"Unsupported autograph method: {autograph_method}")

    sign_req = make_signing_req(input_bytes, keyid)

    log.debug("signing data with format %s with %s", fmt, autograph_method)

    url = f"{key_config.widevine_url}/sign/{autograph_method}"

    sign_resp = await retry_async(
        call_autograph,
        args=(url, key_config["widevine_user"], key_config["widevine_pass"], sign_req),
        attempts=3,
        sleeptime_kwargs={"delay_factor": 2.0},
    )

    if autograph_method == "file":
        return sign_resp[0]["signed_file"]
    else:
        return sign_resp[0]["signature"]


async def sign_file_with_autograph(key_config, from_, fmt, to=None):
    """Signs file with autograph and writes the results to a file.

    Args:
        key_config (dict): the running config for this key
        from_ (str): the source file to sign
        fmt (str): the format to sign with
        to (str, optional): the target path to sign to. If None, overwrite
                            `from_`. Defaults to None.

    Raises:
        Requests.RequestException: on failure

    Returns:
        str: the path to the signed file

    """
    to = to or from_
    input_bytes = open(from_, "rb").read()
    signed_bytes = base64.b64decode(
        await sign_with_autograph(key_config, input_bytes, fmt, "file")
    )
    with open(to, "wb") as fout:
        fout.write(signed_bytes)
    return to


async def sign_hash_with_autograph(key_config, hash_, fmt, keyid=None):
    """Signs hash with autograph and returns the result.

    Args:
        key_config (dict): the running config for this key
        hash_ (bytes): the input hash to sign
        fmt (str): the format to sign with
        keyid (str): which key to use on autograph (optional)

    Raises:
        Requests.RequestException: on failure

    Returns:
        bytes: the signature

    """
    signature = base64.b64decode(
        await sign_with_autograph(key_config, hash_, fmt, "hash", keyid)
    )
    return signature


async def sign_widevine_with_autograph(key_config, from_, blessed, to=None):
    """Create a widevine signature using autograph as a backend.

    Args:
        key_config (dict): the running config for this key
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
    fmt = "autograph_widevine"

    h = widevine.generate_widevine_hash(from_, flags)

    signature = await sign_hash_with_autograph(key_config, h, fmt)

    with open(to, "wb") as fout:
        certificate = open(key_config["widevine_cert"], "rb").read()
        sig = widevine.generate_widevine_signature(signature, certificate, flags)
        fout.write(sig)
    return to
