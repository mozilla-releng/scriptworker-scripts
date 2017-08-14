import json
import mock
import os
import pytest

from scriptworker.context import Context
from signingscript.exceptions import FailedSubprocess, SigningServerError
from signingscript.test import read_file, tmpdir
import signingscript.utils as utils
from . import PUB_KEY_PATH

assert tmpdir  # silence flake8

ID_RSA_PUB_HASH = "226658906e46b26ef195c468f94e2be983b6c53f370dff0d8e725832f" + \
    "4645933de4755690a3438760afe8790a91938100b75b5d63e76ebd00920adc8d2a8857e"

SERVER_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'example_server_config.json')


# mkdir {{{1
def test_mkdir_does_make_dirs(tmpdir):

    def assertDirIsUniqueAndNamed(dirs, name):
        assert len(dirs) == 1
        assert dirs[0].is_dir()
        assert dirs[0].name == name

    end_dir = os.path.join(tmpdir, 'dir_in_the_middle', 'leaf_dir')
    utils.mkdir(end_dir)

    middle_dirs = list(os.scandir(tmpdir))
    assertDirIsUniqueAndNamed(middle_dirs, 'dir_in_the_middle')

    leaf_dirs = list(os.scandir(middle_dirs[0].path))
    assertDirIsUniqueAndNamed(leaf_dirs, 'leaf_dir')


def test_mkdir_mutes_os_errors(mocker):
    m = mocker.patch.object(os, 'makedirs')
    m.side_effect = OSError
    utils.mkdir('/dummy/dir')
    m.assert_called_with('/dummy/dir')


# get_hash {{{1
def test_get_hash():
    assert utils.get_hash(PUB_KEY_PATH, hash_type="sha512") == ID_RSA_PUB_HASH


# load_json {{{1
def test_load_json_from_file(tmpdir):
    json_object = {'a_key': 'a_value'}

    output_file = os.path.join(tmpdir, 'file.json')
    with open(output_file, 'w') as f:
        json.dump(json_object, f)

    assert utils.load_json(output_file) == json_object


# load_signing_server_config {{{1
def test_load_signing_server_config():
    context = Context()
    context.config = {
        'signing_server_config': SERVER_CONFIG_PATH,
    }
    cfg = utils.load_signing_server_config(context)
    assert cfg["dep"][0].server == "server1:9000"
    assert cfg["dep"][1].user == "user2"
    assert cfg["notdep"][0].password == "pass1"
    assert cfg["notdep"][1].formats == ["f2", "f3"]


# log_output {{{1
@pytest.mark.asyncio
async def test_log_output(tmpdir, mocker):
    logged = []
    with open(SERVER_CONFIG_PATH, 'r') as fh:
        contents = fh.read()

    def info(msg):
        logged.append(msg)

    class AsyncIterator:
        def __init__(self):
            self.contents = contents.split('\n')

        async def __aiter__(self):
            return self

        async def __anext__(self):
            while self.contents:
                return self.contents.pop(0).encode('utf-8')

    mocklog = mocker.patch.object(utils, 'log')
    mocklog.info = info
    mockfh = mock.MagicMock()
    aiter = AsyncIterator()
    mockfh.readline = aiter.__anext__
    await utils.log_output(mockfh)
    assert contents.rstrip() == '\n'.join(logged)


# copy_to_dir {{{1
@pytest.mark.parametrize('source,target,expected,exc', ((
    SERVER_CONFIG_PATH, None, os.path.basename(SERVER_CONFIG_PATH), None
), (
    SERVER_CONFIG_PATH, 'foo', 'foo', None
), (
    os.path.join(os.path.dirname(__file__), 'nonexistent_file'), None, None, SigningServerError
)))
def test_copy_to_dir(tmpdir, source, target, expected, exc):
    if exc:
        with pytest.raises(exc):
            utils.copy_to_dir(source, tmpdir, target=target)
    else:
        newpath = utils.copy_to_dir(source, tmpdir, target=target)
        assert newpath == os.path.join(tmpdir, expected)
        contents1 = read_file(source)
        contents2 = read_file(newpath)
        assert contents1 == contents2


def test_copy_to_dir_no_copy():
    assert utils.copy_to_dir(SERVER_CONFIG_PATH, os.path.dirname(SERVER_CONFIG_PATH)) is None


# execute_subprocess {{{1
@pytest.mark.asyncio
@pytest.mark.parametrize('exit_code', (1, 0))
async def test_execute_subprocess(exit_code):
    command = ['bash', '-c', 'exit  {}'.format(exit_code)]
    if exit_code != 0:
        with pytest.raises(FailedSubprocess):
            await utils.execute_subprocess(command)
    else:
        await utils.execute_subprocess(command, cwd="/tmp")
