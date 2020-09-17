import json
import os
from zipfile import ZipFile

import pytest

import addonscript.xpi as xpi


@pytest.fixture(scope="function")
def fake_xpi():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = f"{current_dir}/fake_target.langpack.xpi"
    with ZipFile(path, "r") as langpack_xpi:
        manifest = langpack_xpi.getinfo("manifest.json")
        with langpack_xpi.open(manifest) as f:
            contents = f.read().decode("utf-8")
            return json.loads(contents)


@pytest.mark.parametrize(
    "version,expected_version",
    (
        ("81.0buildid20200914232702", "81.0"),
        ("81.0", "81.0"),
        ("81.0buildid", "81.0"),
        ("81.0buildid202009142", "81.0"),
        ("81.0a1buildid202009142", "81.0"),
        ("81.0b1buildid202009142", "81.0"),
    ),
)
def test_get_stripped_version(version, expected_version):
    assert xpi.get_stripped_version(version) == expected_version


def test_get_langpack_info(fake_xpi):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = f"{current_dir}/fake_target.langpack.xpi"
    langpack = xpi.get_langpack_info(path)
    assert langpack["locale"] == fake_xpi["langpack_id"]
    assert langpack["version"] == fake_xpi["version"]
    assert langpack["id"] == fake_xpi["applications"]["gecko"]["id"]
