#!/usr/bin/env python
"""Functions that interface with rcodesign"""
import asyncio
import logging
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
            log.warn(stderr)
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
    exitcode, _ = await _execute_command(command)
    if exitcode > 0:
        raise RCodesignError(f"Error polling notary service. Exit code {exitcode}")
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
