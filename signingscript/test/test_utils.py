import json
import os

from scriptworker.context import Context
from signingscript.test import tmpdir
import signingscript.utils as utils

assert tmpdir


def test_detached_signatures():
    assert utils.get_detached_signatures(["mar", "gpg", "pgp"]) == [("gpg", ".asc", "text/plain")]


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


def test_load_json_from_file(tmpdir):
    json_object = {'a_key': 'a_value'}

    output_file = os.path.join(tmpdir, 'file.json')
    with open(output_file, 'w') as f:
        json.dump(json_object, f)

    assert utils.load_json(output_file) == json_object


def test_load_signing_server_config():
    context = Context()
    context.config = {
        'signing_server_config': os.path.join(os.path.dirname(__file__),
                                              "example_server_config.json")
    }
    cfg = utils.load_signing_server_config(context)
    assert cfg["dep"][0].server == "server1:9000"
    assert cfg["dep"][1].user == "user2"
    assert cfg["notdep"][0].password == "pass1"
    assert cfg["notdep"][1].formats == ["f2", "f3"]
