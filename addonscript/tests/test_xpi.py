import json
import os
from zipfile import ZipFile

import pytest

import addonscript.xpi as xpi


def make_fake_xpi(xpi_filename):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = f"{current_dir}/{xpi_filename}"
    with ZipFile(path, "r") as langpack_xpi:
        manifest = langpack_xpi.getinfo("manifest.json")
        with langpack_xpi.open(manifest) as f:
            contents = f.read().decode("utf-8")
            return json.loads(contents)


@pytest.fixture(scope="function")
def fake_xpi_with_applications():
    """This function returns an XPI that uses `applications` in the manifest."""
    return make_fake_xpi("fake_target.langpack.xpi")


@pytest.fixture(scope="function")
def fake_xpi_with_bss():
    """This function returns an XPI that uses `browser_specific_settings` in
    the manifest."""
    return make_fake_xpi("fake_target_with_bss.langpack.xpi")


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


def test_get_langpack_info(fake_xpi_with_applications):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = f"{current_dir}/fake_target.langpack.xpi"
    langpack = xpi.get_langpack_info(path)
    assert langpack["locale"] == fake_xpi_with_applications["langpack_id"]
    assert langpack["version"] == fake_xpi_with_applications["version"]
    assert langpack["id"] == fake_xpi_with_applications["applications"]["gecko"]["id"]


def test_get_langpack_info_browser_specific_settings(fake_xpi_with_bss):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = f"{current_dir}/fake_target_with_bss.langpack.xpi"
    langpack = xpi.get_langpack_info(path)
    assert langpack["locale"] == fake_xpi_with_bss["langpack_id"]
    assert langpack["version"] == fake_xpi_with_bss["version"]
    assert langpack["id"] == fake_xpi_with_bss["browser_specific_settings"]["gecko"]["id"]
