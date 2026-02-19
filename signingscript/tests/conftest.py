import os
import tempfile
from contextlib import contextmanager

import pytest
from scriptworker.context import Context

from signingscript.exceptions import SigningScriptError
from signingscript.script import get_default_config
from signingscript.utils import load_autograph_configs, mkdir


def read_file(path):
    with open(path, "r") as fh:
        return fh.read()


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SERVER_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "example_server_config.json")
APPLE_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "example_apple_notarization_config.json")
DEFAULT_SCOPE_PREFIX = "project:releng:signing:"
TEST_CERT_TYPE = f"{DEFAULT_SCOPE_PREFIX}cert:dep-signing"
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PUB_KEY_PATH = os.path.join(TEST_DATA_DIR, "id_rsa.pub")
PUB_KEY = read_file(PUB_KEY_PATH)


def noop_sync(*args, **kwargs):
    pass


async def noop_async(*args, **kwargs):
    pass


@pytest.fixture(scope="function")
def tmpfile():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(bytes("fake", "utf-8"))
        tmp.flush()
        return tmp.name


def die(*args, **kwargs):
    raise SigningScriptError("dying!")


@pytest.fixture(scope="function")
def context(tmpdir):
    context = Context()
    context.config = get_default_config()
    context.config["autograph_configs"] = SERVER_CONFIG_PATH
    context.config["work_dir"] = os.path.join(tmpdir, "work")
    context.config["artifact_dir"] = os.path.join(tmpdir, "artifact")
    context.config["taskcluster_scope_prefixes"] = [DEFAULT_SCOPE_PREFIX]
    context.config["apple_notarization_configs"] = APPLE_CONFIG_PATH
    context.autograph_configs = load_autograph_configs(SERVER_CONFIG_PATH)
    context.apple_credentials_path = "fakepath"
    context.mar_channels = {TEST_CERT_TYPE: ["*"]}
    mkdir(context.config["work_dir"])
    mkdir(context.config["artifact_dir"])
    context.task = {"scopes": [TEST_CERT_TYPE]}
    yield context


@contextmanager
def does_not_raise():
    yield


def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return 1
    elif val in ("n", "no", "f", "false", "off", "0"):
        return 0
    else:
        raise ValueError("invalid truth value {!r}".format(val))


def skip_when_no_autograph_server(function):
    return pytest.mark.skipif(not strtobool(os.environ.get("AUTOGRAPH_INTEGRATION", "false")), reason="Tests requiring an Autograph server are skipped")(
        function
    )
