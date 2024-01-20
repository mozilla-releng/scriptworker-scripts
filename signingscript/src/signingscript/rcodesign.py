#!/usr/bin/env python
"""Functions that interface with rcodesign"""
import asyncio
from collections import namedtuple
import logging
import os
import re
from glob import glob

from scriptworker_client.aio import download_file, raise_future_exceptions, retry_async
from scriptworker_client.exceptions import DownloadError
from signingscript.exceptions import SigningScriptError

log = logging.getLogger(__name__)


class RCodesignError(SigningScriptError):
    pass


async def _execute_command(command):
    """Executes a command, logging output, and return exitcode and output lines
    Args:
        command (str): The command to be run

    Returns:
        (Tuple) exit code, log lines
    """
    log.info("Running command: {}".format(" ".join(command)))
    proc = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    log.info("COMMAND OUTPUT: ")
    output_lines = []
    while True:
        # If at EOF, stop
        if proc.stdout.at_eof() and proc.stderr.at_eof():
            break
        # Handle stdout
        stdout = (await proc.stdout.readline()).decode("utf-8").rstrip()
        if stdout:
            log.info(stdout)
            output_lines.append(stdout)
        # Handle stderr
        stderr = (await proc.stderr.readline()).decode("utf-8").rstrip()
        if stderr:
            # Unfortunately a lot of outputs from rcodesign come out to stderr
            log.warning(stderr)
            output_lines.append(stderr)

    exitcode = await proc.wait()
    log.info("exitcode {}".format(exitcode))
    return exitcode, output_lines


def find_submission_id(logs):
    """Given notarization logs, find and return the submission id
    Args:
        logs (list<str>): Notarization logs

    Returns:
        (str) The submission id
    """
    ids = set()
    for line in logs:
        if "created submission ID: " in line:
            ids.add(line.split(": ")[-1])
    if len(ids) > 1:
        log.error(f"Submission ids: {str(ids)}")
        raise RCodesignError("More than one submission id found in the logs")
    return ids.pop()


async def rcodesign_notarize(app_path, creds_path, staple=False):
    """Call rcodesign notary-submit
    Args:
        app_path (str): Path to notarize
        creds_path (str): Path to credentials file
        staple (boolean): If rcodesign should staple (wait and staple in one go)

    Returns:
        (str) The submission id
    """
    command = ["rcodesign", "notary-submit"]
    if staple:
        command.append("--staple")
    command.extend(["--api-key-path", creds_path, app_path])

    exitcode, logs = await _execute_command(command)
    if exitcode > 0:
        raise RCodesignError(f"Error notarizing app. Exit code {exitcode}")
    return find_submission_id(logs)


async def rcodesign_notary_wait(submission_id, creds_path):
    """Polls Apple services for notarization status
    Args:
        submission_id (str): Notary submission id
        creds_path (str): Path to credentials
    """
    command = [
        "rcodesign",
        "notary-wait",
        "--api-key-path",
        creds_path,
        submission_id,
    ]
    log.info(f"Polling Apple Notary service for notarization status. Submission ID {submission_id}")
    exitcode, logs = await _execute_command(command)
    if exitcode > 0:
        raise RCodesignError(f"Error polling notary service. Exit code {exitcode}")

    await rcodesign_check_result(logs)
    return


async def rcodesign_check_result(logs):
    """Checks notarization results
    rcodesign cli call can exit with 0 even though the notarization has failed
    Args:
        logs (list<str>): output from polling result
    """
    re_inprogress = re.compile("^poll state after.*InProgress$")
    re_accepted = re.compile("^poll state after.*Accepted$")
    re_invalid = re.compile("^poll state after.*Invalid$")
    for line in logs:
        if re_inprogress.search(line):
            continue
        if re_accepted.search(line):
            # Notarization Accepted - should be good
            return
        if re_invalid.search(line):
            raise RCodesignError("Notarization failed!")
    return


async def rcodesign_staple(path):
    """Staples a given app
    Args:
        path (str): Path to be stapled

    Returns:
        (Tuple) exit code, log lines
    """
    command = [
        "rcodesign",
        "staple",
        path,
    ]
    log.info(f"Stapling binary at path {path}")
    exitcode, _ = await _execute_command(command)
    if exitcode > 0:
        raise RCodesignError(f"Error stapling notarization. Exit code {exitcode}")
    return


def _create_empty_entitlements_file(dest):
    contents = """<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
    <plist version="1.0">
    <dict>
    </dict>
    </plist>
    """.lstrip()
    with open(dest, "wt") as fd:
        fd.writelines(contents)


async def _download_entitlements(hardened_sign_config, workdir):
    """Download entitlements listed in the hardened signing config
    Args:
        hardened_sign_config (list): hardened signing configs
        workdir (str): current work directory where entitlements will be saved

    Returns:
        Map of url -> local file location
    """
    empty_file = os.path.join(workdir, "0-empty.xml")
    _create_empty_entitlements_file(empty_file)
    # rcodesign requires us to specify an "empty" entitlements file
    url_map = {None: empty_file}

    # Unique urls to be downloaded
    urls_to_download = set([i["entitlements"] for i in hardened_sign_config if "entitlements" in i])
    # If nothing found, skip
    if not urls_to_download:
        log.warn("No entitlements urls provided! Skipping download.")
        return url_map

    futures = []
    for index, url in enumerate(urls_to_download, start=1):
        # Prefix filename with an index in case filenames are the same
        filename = "{}-{}".format(index, url.split("/")[-1])
        dest = os.path.join(workdir, filename)
        url_map[url] = dest
        log.info(f"Downloading resource: {filename} from {url}")
        futures.append(
            asyncio.ensure_future(
                retry_async(
                    download_file,
                    retry_exceptions=(DownloadError, TimeoutError),
                    args=(url, dest),
                    attempts=5,
                )
            )
        )
    await raise_future_exceptions(futures)
    return url_map


EntitlementEntry = namedtuple(
    "EntitlementEntry",
     ["file", "entitlement", "runtime"],
)

def _get_entitlements_args(hardened_sign_config, path, entitlements_map):
    """Builds the list of entitlements based on files in path

    Args:
        hardened_sign_config (list): hardened signing configuration
        path (str): path to app
    """
    entries = []

    for config in hardened_sign_config:
        entitlement_path = entitlements_map.get(config.get("entitlements"))
        for path_glob in config["globs"]:
            separator = ""
            if not path_glob.startswith("/"):
                separator = "/"
            # Join incoming glob with root of app path
            full_path_glob = path + separator + path_glob
            for binary_path in glob(full_path_glob, recursive=True):
                # Get relative path
                relative_path = os.path.relpath(binary_path, path)
                # Append "<binary path>:<entitlement>" to list of args
                entries.append(
                    EntitlementEntry(
                        file=relative_path,
                        entitlement=entitlement_path,
                        runtime=config.get("runtime"),
                    )
                )

    return entries


async def rcodesign_sign(workdir, path, creds_path, creds_pass_path, hardened_sign_config=[]):
    """Signs a given app
    Args:
        workdir (str): Path to work directory
        path (str): Path to be signed
        creds_path (str): Path to credentials file
        creds_pass_path (str): Path to credentials password file
        hardened_sign_config (list): Hardened signing configuration

    Returns:
        (Tuple) exit code, log lines
    """
    # TODO: Validate and sanitize input
    command = [
        "rcodesign",
        "sign",
        "--code-signature-flags=runtime",
        f"--p12-file={creds_path}",
        f"--p12-password-file={creds_pass_path}",
    ]

    entitlements_map = await _download_entitlements(hardened_sign_config, workdir)
    file_entitlements = _get_entitlements_args(hardened_sign_config, path, entitlements_map)

    def _scoped_arg(arg, basepath, value):
        if basepath == ".":
            return f"--{arg}={value}"
        return f"--{arg}={basepath}:{value}"

    for entry in file_entitlements:
        if entry.runtime:
            flags_arg = _scoped_arg("code-signature-flags", entry.file, "runtime")
            command.append(flags_arg)
        entitlement_arg = _scoped_arg("entitlements-xml-path", entry.file, entry.entitlement)
        command.append(entitlement_arg)

    command.append(path)
    await _execute_command(command)
