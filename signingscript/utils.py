import json
import hashlib
import functools
import logging
from collections import namedtuple

log = logging.getLogger(__name__)
# Mapping between signing client formats and file extensions
DETACHED_SIGNATURES = [
    ('gpg', '.asc', 'text/plain')
]


def get_hash(path, hash_type="sha512"):
    h = hashlib.new(hash_type)
    with open(path, "rb") as f:
        for chunk in iter(functools.partial(f.read, 4096), ''):
            h.update(chunk)
    return h.hexdigest()


def load_signing_server_config(context):
    path = context.config['signing_server_config']
    log.debug("Loading signing server config from {}".format(path))
    SigningServer = namedtuple("SigningServer", ["server", "user", "password",
                                                 "formats"])
    with open(path) as f:
        raw_cfg = json.load(f)

    cfg = {}
    for signing_type, server_data in raw_cfg.items():
        cfg[signing_type] = [SigningServer(*s) for s in server_data]
    log.debug("Signing server config loaded from {}".format(path))
    return cfg


def get_detached_signatures(signing_formats):
    """Returns a list of tuples with detached signature types and corresponding
    file extensions"""
    return [(sig_type, sig_ext, sig_mime) for sig_type, sig_ext, sig_mime in
            DETACHED_SIGNATURES if sig_type in signing_formats]
