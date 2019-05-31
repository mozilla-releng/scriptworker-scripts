"""Signingscript general utility functions."""
import asyncio
from asyncio.subprocess import PIPE, STDOUT
import functools
import hashlib
import json
import logging
import os
from shutil import copyfile
from collections import namedtuple

from signingscript.exceptions import FailedSubprocess, SigningServerError

log = logging.getLogger(__name__)


SigningServer = namedtuple("SigningServer", ["server", "user", "password",
                                             "formats", "server_type"])


def mkdir(path):
    """Equivalent to `mkdir -p`.

    Args:
        path (str): the path to mkdir

    """
    try:
        os.makedirs(path)
        log.info("mkdir {}".format(path))
    except OSError:
        pass


def get_hash(path, hash_type="sha512"):
    """Get the hash of a given path.

    Args:
        path (str): the path to calculate the hash for
        hash_type (str, optional): the algorithm to use.  Defaults to `sha512`

    Returns:
        str: the hexdigest of the hash

    """
    # I'd love to make this async, but evidently file i/o is always ready
    h = hashlib.new(hash_type)
    with open(path, "rb") as f:
        for chunk in iter(functools.partial(f.read, 4096), b''):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    """Load json from path.

    Args:
        path (str): the path to read from

    Returns:
        dict: the loaded json object

    """
    with open(path, "r") as fh:
        return json.load(fh)


def load_signing_server_config(context):
    """Build a specialized signing server config from the `signing_server_config`.

    Args:
        context (Context): the signing context

    Returns:
        dict of lists: keyed by signing cert type, value is a list of SigningServer instances

    """
    path = context.config['signing_server_config']
    log.info("Loading signing server config from {}".format(path))
    with open(path) as f:
        raw_cfg = json.load(f)

    cfg = {}
    for signing_type, server_data in raw_cfg.items():
        cfg[signing_type] = [SigningServer(*s) for s in server_data]
    log.info("Signing server config loaded from {}".format(path))
    return cfg


async def log_output(fh, log_level=logging.INFO):
    """Log the output from an async generator.

    Args:
        fh (async generator): the async generator to log output from
        log_level (int): the logging level

    """
    while True:
        line = await fh.readline()
        if line:
            log.log(log_level, line.decode("utf-8").rstrip())
        else:
            break


def copy_to_dir(source, parent_dir, target=None):
    """Copy `source` to `parent_dir`, optionally renaming.

    Args:
        source (str): the source path
        parent_dir (str): the target parent dir. This doesn't have to exist
        target (str, optional): the basename of the target file.  If None,
            use the basename of `source`. Defaults to None.

    Raises:
        SigningServerError: on failure

    """
    target = target or os.path.basename(source)
    target_path = os.path.join(parent_dir, target)
    try:
        parent_dir = os.path.dirname(target_path)
        mkdir(parent_dir)
        if source != target_path:
            log.info("Copying %s to %s" % (source, target_path))
            copyfile(source, target_path)
            return target_path
        else:
            log.info("Not copying %s to itself" % (source))
    except (IOError, OSError):
        log.exception("Can't copy %s to %s!", source, target_path)
        raise SigningServerError("Can't copy {} to {}!".format(source, target_path))


async def execute_subprocess(command, log_level=logging.INFO, **kwargs):
    """Execute a command in a subprocess.

    Args:
        command (list): the command to run
        log_level (int): the logging level
        **kwargs: the kwargs to pass to subprocess

    Raises:
        FailedSubprocess: on failure

    """
    message = 'Running "{}"'.format(' '.join(command))
    if 'cwd' in kwargs:
        message += " in {}".format(kwargs['cwd'])
    log.info(message)
    subprocess = await asyncio.create_subprocess_exec(
        *command, stdout=PIPE, stderr=STDOUT, **kwargs
    )
    log.log(log_level, "COMMAND OUTPUT: ")
    await log_output(subprocess.stdout, log_level=log_level)
    exitcode = await subprocess.wait()
    log.info("exitcode {}".format(exitcode))

    if exitcode != 0:
        raise FailedSubprocess('Command `{}` failed'.format(' '.join(command)))


def is_autograph_signing_format(format_):
    """Return bool of whether a signing format is for autograph.

    Args:
        format_ (str): the format to check

    """
    return format_ and format_.startswith('autograph_')


def is_apk_autograph_signing_format(format_):
    """Return bool of whether a signing format is an APK.

    Args:
        format_ (str): the format to check

    """
    # TODO Remove autograph_focus once format is migrated
    return format_ and format_.startswith('autograph_apk_') or format_ == 'autograph_focus'


def is_sha1_apk_autograph_signing_format(format_):
    """Return bool of whether format of an APK needs custom signing.

    Args:
        format_ (str): the format to check

    """
    # this list could grow if we wanted to filter out other custom signatures
    return is_apk_autograph_signing_format(format_) and format_.endswith('_sha1')


def split_autograph_format(format_):
    """Return the format and keyid from an autograph format specifier.

    Args:
        format_ (str): the format to use

    Returns:
        format_, keyid: the plain signing format to use, and optional keyid

    """
    if ':' in format_:
        return format_.split(':', 1)
    else:
        return format_, None
