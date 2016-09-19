import asyncio
import functools
import hashlib
import json
import logging
import os
from shutil import copyfile
import traceback
from collections import namedtuple

from signingscript.exceptions import SigningServerError

log = logging.getLogger(__name__)
# Mapping between signing client formats and file extensions
DETACHED_SIGNATURES = [
    ('gpg', '.asc', 'text/plain')
]


def mkdir(path):
    try:
        os.makedirs(path)
        log.info("mkdir {}".format(path))
    except OSError:
        pass


def get_hash(path, hash_type="sha512"):
    # I'd love to make this async, but evidently file i/o is always ready
    h = hashlib.new(hash_type)
    with open(path, "rb") as f:
        for chunk in iter(functools.partial(f.read, 4096), b''):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    with open(path, "r") as fh:
        return json.load(fh)


def load_signing_server_config(context):
    path = context.config['signing_server_config']
    log.info("Loading signing server config from {}".format(path))
    SigningServer = namedtuple("SigningServer", ["server", "user", "password",
                                                 "formats"])
    with open(path) as f:
        raw_cfg = json.load(f)

    cfg = {}
    for signing_type, server_data in raw_cfg.items():
        cfg[signing_type] = [SigningServer(*s) for s in server_data]
    log.info("Signing server config loaded from {}".format(path))
    return cfg


def get_detached_signatures(signing_formats):
    """Returns a list of tuples with detached signature types and corresponding
    file extensions"""
    return [(sig_type, sig_ext, sig_mime) for sig_type, sig_ext, sig_mime in
            DETACHED_SIGNATURES if sig_type in signing_formats]


async def log_output(fh):
    while True:
        line = await fh.readline()
        if line:
            log.info(line.decode("utf-8").rstrip())
        else:
            break


def copy_to_artifact_dir(context, source, target=None):
    artifact_dir = context.config['artifact_dir']
    target = target or os.path.basename(source)
    target_path = os.path.join(artifact_dir, target)
    try:
        parent_dir = os.path.dirname(target_path)
        mkdir(parent_dir)
        log.info("Copying %s to %s" % (source, target_path))
        copyfile(source, target_path)
    except IOError:
        traceback.print_exc()
        raise SigningServerError("Can't copy {} to {}!".format(source, target_path))


async def raise_future_exceptions(tasks):
    await asyncio.wait(tasks)
    for task in tasks:
        exc = task.exception()
        if exc is not None:
            raise exc
