import os
import pytest
import tempfile
from contextlib import contextmanager
from distutils.util import strtobool

from scriptworker.context import Context

from signingscript.exceptions import SigningScriptError
from signingscript.script import get_default_config
from signingscript.utils import mkdir, load_autograph_configs


def read_file(path):
    with open(path, "r") as fh:
        return fh.read()


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SERVER_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "example_server_config.json"
)
DEFAULT_SCOPE_PREFIX = "project:releng:signing:"
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PUB_KEY_PATH = os.path.join(TEST_DATA_DIR, "id_rsa.pub")
PUB_KEY = read_file(PUB_KEY_PATH)


def noop_sync(*args, **kwargs):
    pass


async def noop_async(*args, **kwargs):
    pass


@pytest.yield_fixture(scope="function")
def tmpfile():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(bytes("fake", "utf-8"))
        tmp.flush()
        return tmp.name


def die(*args, **kwargs):
    raise SigningScriptError("dying!")


@pytest.yield_fixture(scope="function")
def context(tmpdir):
    context = Context()
    context.config = get_default_config()
    context.config["autograph_configs"] = SERVER_CONFIG_PATH
    context.config["work_dir"] = os.path.join(tmpdir, "work")
    context.config["artifact_dir"] = os.path.join(tmpdir, "artifact")
    context.config["taskcluster_scope_prefixes"] = [DEFAULT_SCOPE_PREFIX]
    context.autograph_configs = load_autograph_configs(SERVER_CONFIG_PATH)
    mkdir(context.config["work_dir"])
    mkdir(context.config["artifact_dir"])
    yield context


@contextmanager
def does_not_raise():
    yield


def skip_when_no_autograph_server(function):
    return pytest.mark.skipif(
        not strtobool(os.environ.get("AUTOGRAPH_INTEGRATION", "false")),
        reason="Tests requiring an Autograph server are skipped",
    )(function)
