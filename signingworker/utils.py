import fcntl
import json
import socket
import struct
import hashlib
import functools
import logging
from collections import namedtuple

log = logging.getLogger(__name__)


def get_ip_address(interface_name):
    """Return IP address used by specific interface

    :rtype : str
    :param interface_name: Interface name, e.g. eth0
    :return: default IP address used by interface
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', interface_name[:15])
    )[20:24])


# TODO: find a better way to specify source IP, maybe change the signing API
my_ip = get_ip_address("eth0")


def get_hash(path, hash_type="sha512"):
    h = hashlib.new(hash_type)
    with open(path, "rb") as f:
        for chunk in iter(functools.partial(f.read, 4096), ''):
            h.update(chunk)
    return h.hexdigest()


def load_signing_server_config(config):
    log.debug("Loading signing server config from %s", config)
    SigningServer = namedtuple("SigningServer", ["server", "user", "password",
                                                 "formats"])
    with open(config) as f:
        raw_cfg = json.load(f)

    cfg = {}
    for signing_type, server_data in raw_cfg.iteritems():
        cfg[signing_type] = [SigningServer(*s) for s in server_data]
    log.debug("Signing server config loaded from %s", config)
    return cfg
